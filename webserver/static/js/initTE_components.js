import {
    Carousel,
    Collapse,
    Sidenav,
    Ripple,
    Input,
    Modal,
    initTE,
} from "/static/node_modules/tw-elements/dist/js/tw-elements.es.min.js";

initTE({Carousel, Collapse, Sidenav, Ripple, Modal, Input}, true);

if (document.getElementById("sidenav-4")) {
    const sidenav = document.getElementById("sidenav-4");
    const sidenavInstance = Sidenav.getInstance(sidenav);

    let innerWidth = null;

    const setMode = (e) => {
        // Check necessary for Android devices
        if (window.innerWidth === innerWidth) {
            return;
        }

        innerWidth = window.innerWidth;

        if (window.innerWidth < sidenavInstance.getBreakpoint("sm")) {
            sidenavInstance.changeMode("over");
            sidenavInstance.hide();
        } else {
            sidenavInstance.changeMode("side");
            sidenavInstance.show();
        }
    };

    if (window.innerWidth < sidenavInstance.getBreakpoint("sm")) {
        setMode();
    }

// Event listeners
    window.addEventListener("resize", setMode);
}