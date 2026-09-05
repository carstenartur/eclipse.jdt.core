#!/usr/bin/env python3
"""Configure only the disposable diagnostic application, never JDT UI product code."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
manifest = root / 'META-INF/MANIFEST.MF'
text = manifest.read_text()
needle = 'Import-Package: org.osgi.service.prefs'
assert text.count(needle) == 1
manifest.write_text(text.replace(needle, needle + ',\n org.osgi.service.event,\n org.osgi.framework'))
(root / 'src/diagnostics/UIApp.java').write_text('''package diagnostics;

import java.util.Hashtable;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

import org.eclipse.core.resources.ResourcesPlugin;
import org.eclipse.core.runtime.NullProgressMonitor;
import org.eclipse.equinox.app.IApplication;
import org.eclipse.equinox.app.IApplicationContext;
import org.eclipse.swt.widgets.Display;
import org.eclipse.ui.PlatformUI;
import org.eclipse.ui.application.IWorkbenchConfigurer;
import org.eclipse.ui.application.WorkbenchAdvisor;
import org.junit.internal.TextListener;
import org.junit.runner.JUnitCore;
import org.junit.runner.Result;
import org.junit.runner.notification.Failure;
import org.osgi.framework.Bundle;
import org.osgi.framework.BundleContext;
import org.osgi.framework.FrameworkUtil;
import org.osgi.framework.ServiceReference;
import org.osgi.framework.ServiceRegistration;
import org.osgi.service.event.Event;
import org.osgi.service.event.EventAdmin;
import org.osgi.service.event.EventConstants;
import org.osgi.service.event.EventHandler;

/** Runs the unchanged editor assertions only after workbench startup delivery. */
public class UIApp implements IApplication {
    private static final String READY = "jdt1445/diagnostics/startupDelivered";
    private final AtomicBoolean started = new AtomicBoolean();
    private int exitCode = 2;
    private Display display;
    private BundleContext bundleContext;
    private ServiceReference<EventAdmin> eventReference;
    private ServiceRegistration<EventHandler> registration;

    @Override
    public Object start(IApplicationContext context) throws Exception {
        Bundle ownBundle = FrameworkUtil.getBundle(UIApp.class);
        ownBundle.start(Bundle.START_TRANSIENT);
        this.bundleContext = ownBundle.getBundleContext();
        if (this.bundleContext == null) {
            throw new IllegalStateException("Diagnostic bundle has no active context");
        }
        this.display = PlatformUI.createDisplay();
        try {
            PlatformUI.createAndRunWorkbench(this.display, new WorkbenchAdvisor() {
                @Override
                public String getInitialWindowPerspectiveId() {
                    return "org.eclipse.jdt.ui.JavaPerspective";
                }
                @Override
                public void initialize(IWorkbenchConfigurer configurer) {
                    super.initialize(configurer);
                    org.eclipse.ui.ide.IDE.registerAdapters();
                    configurer.setSaveAndRestore(false);
                }
                @Override
                public void postStartup() {
                    eventReference = bundleContext.getServiceReference(EventAdmin.class);
                    if (eventReference == null) {
                        throw new IllegalStateException("EventAdmin missing after workbench startup");
                    }
                    EventAdmin events = bundleContext.getService(eventReference);
                    if (events == null) {
                        throw new IllegalStateException("EventAdmin service unavailable");
                    }
                    Hashtable<String, Object> properties = new Hashtable<>();
                    properties.put(EventConstants.EVENT_TOPIC, READY);
                    registration = bundleContext.registerService(EventHandler.class, event -> {
                        if (started.compareAndSet(false, true)) {
                            display.asyncExec(UIApp.this::runTests);
                        }
                    }, properties);
                    // PartRenderingEngine has already posted APP_STARTUP_COMPLETE before
                    // invoking this hook. Equinox queues this marker after that dispatch,
                    // so startup handlers can finish their synchronous SWT calls first.
                    events.postEvent(new Event(READY, Map.<String, Object>of()));
                    // This is a failure deadline, not a timing-based startup delay.
                    display.timerExec(60000, () -> {
                        if (!started.get()) {
                            System.err.println("UI_HARNESS_STARTUP_TIMEOUT");
                            PlatformUI.getWorkbench().close();
                        }
                    });
                }
            });
            return Integer.valueOf(this.exitCode);
        } finally {
            if (this.registration != null) {
                this.registration.unregister();
            }
            if (this.eventReference != null) {
                this.bundleContext.ungetService(this.eventReference);
            }
            this.display.dispose();
        }
    }

    private void runTests() {
        System.out.println("UI_HARNESS_STARTUP_DISPATCH_COMPLETE");
        try {
            JUnitCore runner = new JUnitCore();
            runner.addListener(new TextListener(System.out));
            Result result = runner.run(SaveParticipantIntegrationTest.class);
            for (Failure failure : result.getFailures()) {
                System.out.println("UI_DIAGNOSTIC_FAILURE " + failure.getTestHeader());
                System.out.println(failure.getTrace());
            }
            System.out.printf("UI_DIAGNOSTIC_RESULT tests=%d failures=%d ignored=%d%n",
                    result.getRunCount(), result.getFailureCount(), result.getIgnoreCount());
            this.exitCode = result.wasSuccessful() ? 0 : 1;
            ResourcesPlugin.getWorkspace().save(true, new NullProgressMonitor());
        } catch (Exception failure) {
            this.exitCode = 2;
            failure.printStackTrace();
        } finally {
            this.display.asyncExec(() -> PlatformUI.getWorkbench().close());
        }
    }

    @Override
    public void stop() {
        Display current = this.display;
        if (current != null && !current.isDisposed()) {
            current.syncExec(() -> {
                if (PlatformUI.isWorkbenchRunning()) {
                    PlatformUI.getWorkbench().close();
                }
            });
        }
    }
}
''')
print('UI_HARNESS waits for queued workbench-startup delivery; assertions unchanged', flush=True)
