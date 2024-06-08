let images, links;

function resize() {
  // width with implicit margin
  const w_width = document.body.getBoundingClientRect().width;
  const ratio = w_width / screen_width;

  for (let i = 0; i < images.length; i++) {
    const img = images[i];
    img.style.width = `${screen_width * ratio}px`;
  }

  for (let i = 0; i < links.length; i++) {
    const link = links[i];
    [elemLeft, elemTop, elemWidth, elemHeight] = link.dataset.loc.split(",");
    link.style.left = elemLeft * ratio + "px";
    link.style.top = elemTop * ratio + "px";
    link.style.width = elemWidth * ratio + "px";
    link.style.height = elemHeight * ratio + "px";
  }
}

document.addEventListener("DOMContentLoaded", function (event) {
  links = document.querySelectorAll("#screenshots > a");
  images = document.querySelectorAll("#screenshots > img");

  window.addEventListener("resize", function () {
    resize();
  });

  resize();

  // Work-around in case the initial resize() was done while no image was loaded yet
  setTimeout(resize, 300);
});
