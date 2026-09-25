/* PocketSmart AI - Professional Frontend Controller */
document.addEventListener("DOMContentLoaded", () => {
    console.log("PocketSmart AI frontend loaded successfully.");

    const plannerForms = document.querySelectorAll("form");
    
    plannerForms.forEach(form => {
        form.addEventListener("submit", async (e) => {
            e.preventDefault(); // Stop standard form reload

            const submitButton = form.querySelector("button[type='submit']");
            const originalButtonText = submitButton ? submitButton.textContent : "Submit";
            
            // Collect all form fields into a plain JavaScript object
            const formData = new FormData(form);
            let detailsObj = {};
            for (let [key, value] of formData.entries()) {
                detailsObj[key] = value;
            }

            // Determine category based on current URL path
            let category = "General Planner";
            const path = window.location.pathname;
            if (path.includes("home")) category = "Home Interior Planner";
            else if (path.includes("party")) category = "Party Planner";
            else if (path.includes("jewelry")) category = "Jewelry Planner";

            // Format payload to match backend Pydantic model (PlannerInput)
            const payload = {
                category: category,
                details: JSON.stringify(detailsObj) // Converts form inputs into clean JSON string
            };

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = "Generating AI Recommendations...";
                submitButton.style.opacity = "0.7";
            }

            try {
                const response = await fetch(form.action || window.location.href, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json" // Crucial for Pydantic
                    },
                    body: JSON.stringify(payload)
                });

                const contentType = response.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    const data = await response.json();
                    
                    if (response.ok) {
                        // Store result safely and show it or redirect
                        sessionStorage.setItem("ai_recommendations", JSON.stringify(data, null, 2));
                        alert("AI Recommendations Generated Successfully!\n\n" + data.recommendations.substring(0, 150) + "...");
                        
                        resetButtonState(submitButton, originalButtonText);
                    } else {
                        alert("Error: " + (data.detail || "Something went wrong."));
                        resetButtonState(submitButton, originalButtonText);
                    }
                } else {
                    window.location.reload();
                }
            } catch (error) {
                alert("Network Error: " + error.message);
                resetButtonState(submitButton, originalButtonText);
            }
        });
    });

    function resetButtonState(button, text) {
        if (button) {
            button.disabled = false;
            button.textContent = text;
            button.style.opacity = "1";
        }
    }
});