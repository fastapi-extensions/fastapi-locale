document$.subscribe(() => {
  // Diagrams are much wider than the text column. Each one becomes a link to its own file,
  // where the browser shows it at full size and can zoom, scroll and search it.
  for (const image of document.querySelectorAll('.md-content img[src$=".svg"]')) {
    if (image.closest("a")) {
      continue;
    }
    const link = document.createElement("a");
    link.href = image.src;
    link.title = "Open the diagram at full size";
    image.replaceWith(link);
    link.append(image);
  }

  // The theme's search dialog has no accessible name, so screen readers announce it as "dialog".
  document.querySelector('[data-md-component="search"]')?.setAttribute("aria-label", "Search");
});
