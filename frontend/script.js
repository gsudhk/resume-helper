let extractedResumeText = "";  // will store extracted text from PDF

// Extract text from uploaded PDF
document.getElementById("resumeFile").addEventListener("change", function (e) {
  let file = e.target.files[0];
  if (file && file.type === "application/pdf") {
    let fileReader = new FileReader();
    fileReader.onload = function () {
      let typedarray = new Uint8Array(this.result);

      pdfjsLib.getDocument(typedarray).promise.then(function (pdf) {
        let textPromises = [];
        for (let i = 1; i <= pdf.numPages; i++) {
          textPromises.push(
            pdf.getPage(i).then(function (page) {
              return page.getTextContent().then(function (textContent) {
                return textContent.items.map(item => item.str).join(" ");
              });
            })
          );
        }
        return Promise.all(textPromises);
      }).then(function (texts) {
        extractedResumeText = texts.join(" ");
        alert("✅ Resume uploaded and processed successfully!");
      });
    };
    fileReader.readAsArrayBuffer(file);
  } else {
    alert("Please upload a valid PDF file.");
  }
});

// Analyzer function
function analyze() {
  let resumeText = extractedResumeText.toLowerCase();
  let jobText = document.getElementById("jobdesc").value.toLowerCase();

  if (!resumeText) {
    alert("Please upload a Resume PDF first!");
    return;
  }
  if (!jobText) {
    alert("Please paste the Job Description!");
    return;
  }

  let resumeWords = new Set(resumeText.split(/[\s,.;:\n]+/).filter(w => w.length > 2));
  let jobWords = new Set(jobText.split(/[\s,.;:\n]+/).filter(w => w.length > 2));

  let matches = [...resumeWords].filter(w => jobWords.has(w));
  let additions = [...jobWords].filter(w => !resumeWords.has(w));
  let deletions = [...resumeWords].filter(w => !jobWords.has(w));

  function renderTags(list, containerId, type) {
    let container = document.getElementById(containerId);
    container.innerHTML = "";
    if (list.length === 0) {
      container.innerHTML = "<p style='color:#6b7280;'>None</p>";
    } else {
      list.forEach(word => {
        let span = document.createElement("span");
        span.className = "tag " + type;
        span.textContent = word;
        container.appendChild(span);
      });
    }
  }

  renderTags(matches, "matches", "match");
  renderTags(additions, "additions", "add");
  renderTags(deletions, "deletions", "delete");
}
