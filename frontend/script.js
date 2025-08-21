// script.js
const API_BASE_URL = "http://127.0.0.1:8000";

// Handle file upload
document.getElementById("resumeFile").addEventListener("change", async function (e) {
    const file = e.target.files[0];
    const analyzeBtn = document.getElementById("analyzeBtn");

    if (file && file.type === "application/pdf") {
        const formData = new FormData();
        formData.append("file", file);

        analyzeBtn.disabled = true;
        analyzeBtn.textContent = "Processing PDF...";

        try {
            const res = await fetch(`${API_BASE_URL}/upload-pdf`, {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || "PDF processing failed.");
            }

            const data = await res.json();
            alert("✅ " + data.message);

        } catch (error) {
            alert("❌ Error: " + error.message);
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = "Analyze";
        }
    } else {
        alert("Please upload a valid PDF file.");
    }
});

// Handle analysis
async function analyze() {
    const jobText = document.getElementById("jobDesc").value;
    const analyzeBtn = document.getElementById("analyzeBtn");
    
    if (!jobText.trim()) {
        alert("Please paste the Job Description!");
        return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";

    // Clear previous results
    document.getElementById("scoreContainer").textContent = "0%";
    document.getElementById("matchesContainer").innerHTML = "";
    document.getElementById("missingContainer").innerHTML = "";

    try {
        const formData = new FormData();
        formData.append("job_description", jobText);

        const res = await fetch(`${API_BASE_URL}/analyze`, {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.detail || "Analysis failed.");
        }

        const data = await res.json();
        
        // Render the new results
        document.getElementById("scoreContainer").textContent = data.score + "%";
        renderTags(data.matches, "matchesContainer", "match");
        renderTags(data.missing, "missingContainer", "delete");

    } catch (error) {
        alert("❌ Error: " + error.message);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "Analyze";
    }
}

function renderTags(list, containerId, type) {
    const container = document.getElementById(containerId);
    container.innerHTML = ""; // Clear previous tags
    if (!list || list.length === 0 || (list.length === 1 && list[0] === "")) {
        container.innerHTML = "<p class='no-tags'>None found.</p>";
    } else {
        list.forEach(word => {
            if (word) { // Ensure the word is not an empty string
                const span = document.createElement("span");
                span.className = "tag " + type;
                span.textContent = word;
                container.appendChild(span);
            }
        });
    }
}