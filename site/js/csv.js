function getDownloadFilenameFromResponse(response, fallbackName) {
    const disposition = response.headers.get("Content-Disposition") || "";
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match && utf8Match[1])
        return decodeURIComponent(utf8Match[1]);

    const basicMatch = disposition.match(/filename="?([^"]+)"?/i);
    if (basicMatch && basicMatch[1])
        return basicMatch[1];

    return fallbackName;
}

async function triggerFileDownload(url, fallbackName) {
    const response = await fetch(url, { credentials: "same-origin" });
    if (!response.ok)
        throw new Error("Download failed with status " + response.status);

    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = getDownloadFilenameFromResponse(response, fallbackName);
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
}

// Downloads a .csv file from the server
async function downloadCsv() {
    // Get the aggregation bucket
    let bucket = "day";
    if (document.getElementById("csv_res_rad_month").checked == true)
        bucket = "month";
    else if (document.getElementById("csv_res_rad_year").checked == true)
        bucket = "year";

    // Get the date
    let year = document.getElementById('csv_selection_year2').value.toString();
    let month = padStr(document.getElementById('csv_selection_month2').value.toString());
    let day = padStr(document.getElementById('csv_selection_day2').value.toString());

    let prefix = "";
    if (document.getElementById("csv_range_rad_all").checked == true)
        prefix = "";
    else if (document.getElementById("csv_range_rad_year").checked == true)
        prefix = year;
    else if (document.getElementById("csv_range_rad_month").checked == true)
        prefix = year + "-" + month;
    else if (document.getElementById("csv_range_rad_day").checked == true)
        prefix = year + "-" + month + "-" + day;

    // Build query
    let url = ((typeof gBaseUrl === "string" && gBaseUrl.length > 0)
        ? gBaseUrl
        : new URL(".", window.location.href).href) + "api/csv?bucket=" + bucket;
    if (prefix.length > 0)
        url += "&prefix=" + prefix;

    const scope = prefix.length > 0 ? prefix : "all";
    const fallbackName = "phocos_" + bucket + "_" + scope + ".csv";
    try {
        await triggerFileDownload(url, fallbackName);
    }
    catch (error) {
        console.error("CSV download failed.", error);
        alert("The download failed.");
    }
}
