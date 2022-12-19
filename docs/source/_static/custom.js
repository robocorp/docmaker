window.addEventListener("DOMContentLoaded", function (e) {
  const options = {
    log: true,
    inPageLinks: true,
    checkOrigin: false,
    sizeWidth: true,
    widthCalculationMethod: "max",
  };

  iFrameResize(options, "#libdoc");
});
