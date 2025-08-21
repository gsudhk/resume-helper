let extractedResumeText = "";  // will store extracted text from PDF

// Upload PDF to backend
document.getElementById("resumeFile").addEventListener("change", async function (e) {
  let file = e.target.files[0];
  if (file && file.type === "application/pdf") {
    let formData = new FormData();
    formData.append("file", file);

    const res = await fetch("http://localhost:8000/upload-pdf", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.message) {
      alert("✅ Resume uploaded and processed successfully!");
    } else {
      alert(data.error || "Failed to upload resume.");
    }
  } else {
    alert("Please upload a valid PDF file.");
  }
});

// Analyze job description with backend
async function analyze() {
  let jobText = document.getElementById("jobdesc").value;
  if (!jobText) {
    alert("Please paste the Job Description!");
    return;
  }

  let formData = new FormData();
  formData.append("job_description", jobText);

  const res = await fetch("http://localhost:8000/analyze", {
    method: "POST",
    body: formData
  });
  const data = await res.json();

  function renderTags(list, containerId, type) {
    let container = document.getElementById(containerId);
    container.innerHTML = "";
    if (!list || list.length === 0) {
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

  renderTags(data.matches, "matches", "match");
  renderTags(data.additions, "additions", "add");
  renderTags(data.deletions, "deletions", "delete");
}