const Version = "0.32.1";

function setVersion() {
  const versionNode = document.getElementById("version");
  if (versionNode == null)
    return;
  versionNode.textContent = "";
  versionNode.style.display = "none";
}
