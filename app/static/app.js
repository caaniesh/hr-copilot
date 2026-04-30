const state = {
  view: "criteria",
  jobContext: {
    role: "",
    experience_level: "Experienced",
    required_skills: [],
  },
  selectedFile: null,
  analysis: null,
  activeTab: "insights",
  interviewQuestionIndex: 0,
  codingQuestionsVisible: false,
  interviewSuggestionVisible: false,
  assistantOpen: false,
  assistantLoading: false,
  assistantMessages: [],
};

const elements = {
  topbarLeft: document.getElementById("topbarLeft"),
  topbarActions: document.getElementById("topbarActions"),
  criteriaForm: document.getElementById("criteriaForm"),
  roleInput: document.getElementById("role"),
  experienceLevelInput: document.getElementById("experienceLevel"),
  requiredSkillsInput: document.getElementById("requiredSkills"),
  criteriaMessage: document.getElementById("criteriaMessage"),
  uploadMessage: document.getElementById("uploadMessage"),
  analysisMessage: document.getElementById("analysisMessage"),
  interviewMessage: document.getElementById("interviewMessage"),
  dropZone: document.getElementById("dropZone"),
  resumeFileInput: document.getElementById("resumeFile"),
  browseBtn: document.getElementById("browseBtn"),
  changeFileBtn: document.getElementById("changeFileBtn"),
  uploadAnalyzeBtn: document.getElementById("uploadAnalyzeBtn"),
  uploadEmptyState: document.getElementById("uploadEmptyState"),
  uploadSelectedState: document.getElementById("uploadSelectedState"),
  selectedFileName: document.getElementById("selectedFileName"),
  candidateName: document.getElementById("candidateName"),
  candidateLevel: document.getElementById("candidateLevel"),
  candidateContactList: document.getElementById("candidateContactList"),
  overallScore: document.getElementById("overallScore"),
  skillPointsLabel: document.getElementById("skillPointsLabel"),
  experiencePointsLabel: document.getElementById("experiencePointsLabel"),
  projectPointsLabel: document.getElementById("projectPointsLabel"),
  skillPointsBar: document.getElementById("skillPointsBar"),
  experiencePointsBar: document.getElementById("experiencePointsBar"),
  projectPointsBar: document.getElementById("projectPointsBar"),
  recommendationBadge: document.getElementById("recommendationBadge"),
  roleMismatchBanner: document.getElementById("roleMismatchBanner"),
  summaryCardRow: document.getElementById("summaryCardRow"),
  confidenceStrip: document.getElementById("confidenceStrip"),
  recommendationDetailBlock: document.getElementById("recommendationDetailBlock"),
  whyScoreBlock: document.getElementById("whyScoreBlock"),
  downloadReportBtn: document.getElementById("downloadReportBtn"),
  tabInsights: document.getElementById("tab-insights"),
  tabSkills: document.getElementById("tab-skills"),
  tabQuestions: document.getElementById("tab-questions"),
  tabProjects: document.getElementById("tab-projects"),
  interviewContext: document.getElementById("interviewContext"),
  interviewAction: document.getElementById("interviewAction"),
  getSuggestionBtn: document.getElementById("getSuggestionBtn"),
  copilotSuggestionBox: document.getElementById("copilotSuggestionBox"),
  copilotUserBubble: document.getElementById("copilotUserBubble"),
  copilotSuggestedQuestion: document.getElementById("copilotSuggestedQuestion"),
  copilotExpectedDirection: document.getElementById("copilotExpectedDirection"),
  copilotDifficulty: document.getElementById("copilotDifficulty"),
  copilotCoachingNote: document.getElementById("copilotCoachingNote"),
  copilotReason: document.getElementById("copilotReason"),
  interviewCommandInput: document.getElementById("interviewCommandInput"),
  interviewStrengthsList: document.getElementById("interviewStrengthsList"),
  interviewWeaknessesList: document.getElementById("interviewWeaknessesList"),
  interviewPrimarySkills: document.getElementById("interviewPrimarySkills"),
  generateCodingBtn: document.getElementById("generateCodingBtn"),
  codingQuestionStack: document.getElementById("codingQuestionStack"),
  preparedQuestionList: document.getElementById("preparedQuestionList"),
  assistantWidget: document.getElementById("assistantWidget"),
  assistantContextLine: document.getElementById("assistantContextLine"),
  assistantQuickActions: document.getElementById("assistantQuickActions"),
  assistantThread: document.getElementById("assistantThread"),
  assistantForm: document.getElementById("assistantForm"),
  assistantInput: document.getElementById("assistantInput"),
  assistantSendBtn: document.getElementById("assistantSendBtn"),
  assistantCloseBtn: document.getElementById("assistantCloseBtn"),
  chatFab: document.getElementById("chatFab"),
};

const viewElements = Array.from(document.querySelectorAll(".view"));
const tabButtons = Array.from(document.querySelectorAll(".analysis-tab"));

renderTopbar();
syncUploadState();
renderAssistant();

elements.criteriaForm.addEventListener("submit", (event) => {
  event.preventDefault();
  continueToUpload();
});

elements.browseBtn.addEventListener("click", () => openFilePicker());
elements.changeFileBtn.addEventListener("click", () => openFilePicker());
elements.uploadAnalyzeBtn.addEventListener("click", () => analyzeResume());
elements.getSuggestionBtn.addEventListener("click", () => getInterviewSuggestion());
elements.downloadReportBtn.addEventListener("click", () => downloadCandidateReport());
elements.generateCodingBtn.addEventListener("click", () => toggleCodingQuestions());
elements.chatFab.addEventListener("click", () => toggleAssistant());
elements.assistantCloseBtn.addEventListener("click", () => closeAssistant());
elements.assistantForm.addEventListener("submit", (event) => void handleAssistantSubmit(event));
elements.assistantQuickActions.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-question]");
  if (!button) {
    return;
  }
  void submitAssistantQuestion(button.dataset.question);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.assistantOpen) {
    closeAssistant();
  }
});

elements.resumeFileInput.addEventListener("change", (event) => {
  const [file] = event.target.files;
  if (file) {
    setSelectedFile(file);
  }
});

elements.dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  elements.dropZone.classList.add("drag-active");
});

elements.dropZone.addEventListener("dragleave", () => {
  elements.dropZone.classList.remove("drag-active");
});

elements.dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  elements.dropZone.classList.remove("drag-active");
  const [file] = event.dataTransfer.files;
  if (file) {
    setSelectedFile(file);
  }
});

elements.dropZone.addEventListener("click", (event) => {
  if (event.target.closest("button")) {
    return;
  }
  if (!state.selectedFile) {
    openFilePicker();
  }
});

elements.topbarActions.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const action = button.dataset.action;
  if (action === "view-dashboard") {
    goToDashboard();
    return;
  }
  if (action === "back-to-criteria") {
    setView("criteria");
    return;
  }
  if (action === "back-to-dashboard") {
    setView("criteria");
    setCriteriaMessage("Criteria are preserved. You can upload another resume at any time.");
    return;
  }
  if (action === "back-to-analysis") {
    setView("analysis");
    setInterviewMessage("");
    return;
  }
  if (action === "start-interview") {
    startInterview();
  }
});

document.getElementById("analysisTabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (!button) {
    return;
  }
  setActiveTab(button.dataset.tab);
});

function renderTopbar() {
  elements.topbarLeft.innerHTML = renderNitcoLogo();

  if (state.view === "criteria") {
    elements.topbarActions.innerHTML = renderTopbarPanel(
      "AI Interview Copilot",
      "Enterprise HR Agent",
      state.analysis
        ? '<button type="button" class="btn btn-secondary" data-action="view-dashboard">View Dashboard</button>'
        : ""
    );
    return;
  }

  if (state.view === "upload") {
    elements.topbarActions.innerHTML = renderTopbarPanel(
      "Upload Resume",
      "Step 2 of 4",
      `
        <button type="button" class="btn btn-outline" data-action="back-to-criteria">Back</button>
        <button type="button" class="btn btn-secondary" data-action="view-dashboard">Dashboard</button>
      `
    );
    return;
  }

  if (state.view === "interview") {
    const candidateName = state.analysis?.candidate?.name || "Candidate";
    const score = state.analysis?.score_breakdown?.final_score ?? 0;
    elements.topbarActions.innerHTML = renderTopbarPanel(
      "Interview Copilot",
      `${candidateName} - Score: ${Math.round(Number(score))}/100`,
      '<button type="button" class="btn btn-outline" data-action="back-to-analysis">Back to Analysis</button>'
    );
    return;
  }

  elements.topbarActions.innerHTML = renderTopbarPanel(
    "Candidate Analysis",
    "Explainable AI evaluation",
    `
      <button type="button" class="btn btn-outline" data-action="back-to-dashboard">Back to Dashboard</button>
      <button type="button" class="btn btn-primary" data-action="start-interview">Start Interview Mode</button>
    `
  );
}

function renderNitcoLogo() {
  return `
    <div class="nitco-lockup" aria-label="NITCO">
      <img
        src="/static/nitco_logo.png"
        alt="NITCO"
        class="nitco-logo-image"
      >
    </div>
  `;
}

function renderTopbarPanel(title, subtitle, actionsMarkup) {
  return `
    <div class="topbar-panel">
      <div class="topbar-title-stack">
        <h2 class="page-title">${title}</h2>
        <p class="topbar-subtitle">${subtitle}</p>
      </div>
      <div class="topbar-button-row">
        ${actionsMarkup}
      </div>
    </div>
  `;
}

function setView(view) {
  state.view = view;
  for (const section of viewElements) {
    section.classList.toggle("view-active", section.id === `view-${view}`);
  }
  renderTopbar();
  if (view === "upload") {
    syncUploadState();
  }
  elements.chatFab.style.display = "inline-flex";
  renderAssistant();
}

function continueToUpload() {
  const role = elements.roleInput.value.trim();
  const requiredSkills = parseSkills(elements.requiredSkillsInput.value);
  const experienceLevel = elements.experienceLevelInput.value;

  if (!role) {
    setCriteriaMessage("Job role is required.", true);
    return;
  }
  if (!requiredSkills.length) {
    setCriteriaMessage("Please provide at least one required skill.", true);
    return;
  }

  state.jobContext = {
    role,
    experience_level: experienceLevel,
    required_skills: requiredSkills,
  };

  setCriteriaMessage("");
  setUploadMessage("");
  setView("upload");
}

function setSelectedFile(file) {
  state.selectedFile = file;
  syncUploadState();
  setUploadMessage("");
}

function syncUploadState() {
  const hasFile = Boolean(state.selectedFile);
  elements.uploadEmptyState.style.display = hasFile ? "none" : "grid";
  elements.uploadSelectedState.style.display = hasFile ? "grid" : "none";
  elements.selectedFileName.textContent = hasFile ? state.selectedFile.name : "No file selected";
}

async function analyzeResume() {
  if (!state.selectedFile) {
    setUploadMessage("Please select a resume file before continuing.", true);
    return;
  }

  const fileType = state.selectedFile.name.split(".").pop().toLowerCase();
  if (!["pdf", "doc", "docx", "txt"].includes(fileType)) {
    setUploadMessage("Please upload a PDF, DOC, DOCX, or TXT resume.", true);
    return;
  }

  elements.uploadAnalyzeBtn.disabled = true;
  elements.uploadAnalyzeBtn.textContent = "Uploading...";
  setUploadMessage("Uploading and analyzing the selected resume...");

  try {
    const formData = new FormData();
    formData.append("file", state.selectedFile);

    const uploadResponse = await fetch("/upload_resume", {
      method: "POST",
      body: formData,
    });
    const uploadResult = await uploadResponse.json();
    if (!uploadResponse.ok) {
      throw new Error(uploadResult.detail || "Resume upload failed.");
    }

    elements.uploadAnalyzeBtn.textContent = "Analyzing...";
    const analyzeResponse = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        upload_id: uploadResult.upload_id,
        job_context: state.jobContext,
        coding_submissions: [],
      }),
    });

    const analysisResult = await analyzeResponse.json();
    if (!analyzeResponse.ok) {
      throw new Error(analysisResult.detail || "Analysis failed.");
    }

    state.analysis = analysisResult;
    state.activeTab = "insights";
    state.interviewQuestionIndex = 0;
    state.codingQuestionsVisible = false;
    state.interviewSuggestionVisible = false;
    renderAnalysis();
    setView("analysis");
    setAnalysisMessage(`Analysis completed for ${analysisResult.candidate.name || "the candidate"}.`);
  } catch (error) {
    setUploadMessage(error.message, true);
  } finally {
    elements.uploadAnalyzeBtn.disabled = false;
    elements.uploadAnalyzeBtn.textContent = "Upload & Analyze";
  }
}

function downloadCandidateReport() {
  const id = state.analysis?.candidate?.candidate_id;
  if (!id) {
    return;
  }
  window.location.href = `/export?candidate_id=${encodeURIComponent(id)}`;
}

function renderSummaryCardHtml(card) {
  if (!card) {
    return "";
  }
  return `
    <div class="summary-pills">
      <div class="summary-pill"><span>Fit level</span><strong>${escapeHtml(card.fit_level)}</strong></div>
      <div class="summary-pill"><span>Best role fit</span><strong>${escapeHtml(card.best_role)}</strong></div>
      <div class="summary-pill"><span>Hiring risk</span><strong>${escapeHtml(card.hiring_risk)}</strong></div>
    </div>
  `;
}

function renderAnalysis() {
  const {
    candidate,
    score_breakdown: score,
    final_decision,
    insights,
    warnings,
    confidence,
    summary_card,
    why_this_score,
    role_mismatch_warning,
  } = state.analysis;
  const experienceLevel = state.jobContext.experience_level;
  const scoreWeights = score.weights || {};
  const scoreLines = [
    {
      value: weightedPoints(score.skill_score, scoreWeights.skills || 0),
      max: scoreWeights.skills || 0,
    },
    {
      value: weightedPoints(score.experience_score, scoreWeights.experience || 0),
      max: scoreWeights.experience || 0,
    },
    {
      value: weightedPoints(score.project_score, scoreWeights.projects || 0),
      max: scoreWeights.projects || 0,
    },
  ];

  elements.candidateName.textContent = candidate.name || "Candidate Name Not Detected";
  elements.candidateLevel.textContent = experienceLevel;
  elements.candidateContactList.innerHTML = `
    <div class="contact-item"><span class="contact-icon">&#9993;</span><span>${candidate.email || "Email not detected"}</span></div>
    <div class="contact-item"><span class="contact-icon">&#9742;</span><span>${candidate.phone || "Phone not detected"}</span></div>
    <div class="contact-item"><span class="contact-icon">&#9679;</span><span>${candidate.location || "Location not detected"}</span></div>
  `;

  elements.overallScore.textContent = `${Math.round(score.final_score)}/100`;

  if (elements.roleMismatchBanner) {
    if (role_mismatch_warning) {
      elements.roleMismatchBanner.hidden = false;
      elements.roleMismatchBanner.textContent = role_mismatch_warning;
    } else {
      elements.roleMismatchBanner.hidden = true;
      elements.roleMismatchBanner.textContent = "";
    }
  }

  if (elements.summaryCardRow) {
    elements.summaryCardRow.innerHTML = renderSummaryCardHtml(summary_card);
  }

  if (elements.confidenceStrip && confidence) {
    const label = confidence.confidence_label || confidence.band || "—";
    const pct = Math.round(Number(confidence.confidence_score ?? confidence.score ?? 0));
    elements.confidenceStrip.textContent = `Confidence: ${label} (${pct}%)`;
  }

  updateScoreLine(elements.skillPointsLabel, elements.skillPointsBar, scoreLines[0].value, scoreLines[0].max);
  updateScoreLine(elements.experiencePointsLabel, elements.experiencePointsBar, scoreLines[1].value, scoreLines[1].max);
  updateScoreLine(elements.projectPointsLabel, elements.projectPointsBar, scoreLines[2].value, scoreLines[2].max);

  elements.recommendationBadge.textContent = formatRecommendation(final_decision.recommendation);
  elements.recommendationBadge.className = `recommendation-badge ${recommendationClass(final_decision.recommendation)}`;

  if (elements.recommendationDetailBlock) {
    const recConf = final_decision.recommendation_confidence || final_decision.confidence || "—";
    const alt = final_decision.alternative_role_suggestion;
    elements.recommendationDetailBlock.innerHTML = `
      <dl class="rec-detail-list">
        <dt>Recommendation</dt>
        <dd>${escapeHtml(formatRecommendation(final_decision.recommendation))}</dd>
        <dt>Confidence</dt>
        <dd>${escapeHtml(recConf)}</dd>
        ${alt ? `<dt>Better fit</dt><dd>${escapeHtml(alt)}</dd>` : ""}
      </dl>
    `;
  }

  if (elements.whyScoreBlock) {
    const bullets = why_this_score && why_this_score.length ? why_this_score : [];
    elements.whyScoreBlock.innerHTML = bullets.length
      ? `<h4 id="whyScoreHeading">Why this score?</h4><ul>${bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>`
      : `<h4 id="whyScoreHeading">Why this score?</h4><p class="empty-copy">No additional breakdown was generated.</p>`;
  }

  elements.tabInsights.innerHTML = renderInsights(insights, warnings);
  elements.tabSkills.innerHTML = renderSkills(state.analysis.skill_analysis, state.analysis.skill_buckets);
  elements.tabQuestions.innerHTML = renderQuestions(state.analysis.questions);
  elements.tabProjects.innerHTML = renderProjects(candidate.projects);

  setActiveTab(state.activeTab);
}

function renderInterviewPage() {
  if (!state.analysis) {
    return;
  }

  const analysis = state.analysis;
  const primarySkills = analysis.skill_analysis.primary_skills || [];
  const activeQuestion =
    analysis.questions?.[state.interviewQuestionIndex] ||
    analysis.questions?.[0] ||
    null;

  elements.copilotSuggestionBox.classList.toggle("is-visible", state.interviewSuggestionVisible);

  elements.interviewStrengthsList.innerHTML = renderListItems(
    analysis.insights.strengths,
    "No strengths were generated."
  );
  elements.interviewWeaknessesList.innerHTML = renderListItems(
    analysis.insights.weaknesses,
    "No areas to probe were generated."
  );
  elements.interviewPrimarySkills.innerHTML = primarySkills.length
    ? primarySkills
        .map((skill) => `<span class="skill-chip skill-chip-primary">${skill.name}</span>`)
        .join("")
    : `<p class="empty-copy">No primary skills detected.</p>`;

  if (activeQuestion) {
    elements.copilotUserBubble.textContent = "Share interview context and request a suggestion to start the agent conversation.";
    elements.copilotSuggestedQuestion.textContent = activeQuestion.question;
    elements.copilotExpectedDirection.textContent = activeQuestion.expected_answer;
    elements.copilotDifficulty.textContent = activeQuestion.difficulty;
    elements.copilotCoachingNote.textContent = `Start with ${inferQuestionCategory(activeQuestion)} and listen for concrete implementation details.`;
    if (elements.copilotReason) {
      elements.copilotReason.textContent = activeQuestion.why_this_question || "Tied to the candidate's stated project work.";
    }
  } else {
    elements.copilotUserBubble.textContent = "No interview context has been captured yet.";
    elements.copilotSuggestedQuestion.textContent = "No prepared question is available yet.";
    elements.copilotExpectedDirection.textContent = "---";
    elements.copilotDifficulty.textContent = "---";
    elements.copilotCoachingNote.textContent = "---";
    if (elements.copilotReason) {
      elements.copilotReason.textContent = "---";
    }
  }

  elements.codingQuestionStack.classList.toggle("is-visible", state.codingQuestionsVisible);
  elements.codingQuestionStack.innerHTML = state.codingQuestionsVisible
    ? renderCodingQuestions(analysis.coding_assessment.questions || [])
    : "";

  elements.preparedQuestionList.innerHTML = renderPreparedQuestions(analysis.questions || []);
  elements.generateCodingBtn.textContent = state.codingQuestionsVisible
    ? "Hide Coding Question"
    : "Generate Coding Question";
}

async function getInterviewSuggestion() {
  if (!state.analysis) {
    return;
  }

  elements.getSuggestionBtn.disabled = true;
  elements.getSuggestionBtn.textContent = "Loading...";
  setInterviewMessage("Fetching an interview suggestion...");

  try {
    const typedCommand = (elements.interviewCommandInput?.value || "").trim();
    const command = typedCommand || elements.interviewAction.value;

    const response = await fetch("/copilot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        candidate_id: state.analysis.candidate.candidate_id,
        version_id: state.analysis.candidate.version_id,
        hr_command: command,
        command,
        current_question_index: state.interviewQuestionIndex,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "Unable to get a copilot suggestion.");
    }

    if (command === "next question" && state.interviewQuestionIndex < state.analysis.questions.length - 1) {
      state.interviewQuestionIndex += 1;
    }

    const contextNote = elements.interviewContext.value.trim();
    const actionLabel = selectedActionLabel();
    state.interviewSuggestionVisible = true;
    elements.copilotSuggestionBox.classList.add("is-visible");
    elements.copilotUserBubble.textContent = contextNote
      ? `${actionLabel}: ${contextNote}`
      : `${actionLabel}: Guide me to the best next move in this interview.`;
    elements.copilotSuggestedQuestion.textContent = result.suggested_question;
    elements.copilotExpectedDirection.textContent = result.expected_direction;
    elements.copilotDifficulty.textContent = result.difficulty;
    elements.copilotCoachingNote.textContent = result.coaching_note;
    if (elements.copilotReason) {
      elements.copilotReason.textContent = result.reason || result.coaching_note || "—";
    }
    setInterviewMessage("Suggestion updated.");
  } catch (error) {
    setInterviewMessage(error.message, true);
  } finally {
    elements.getSuggestionBtn.disabled = false;
    elements.getSuggestionBtn.textContent = "Get Suggestion";
  }
}

function toggleCodingQuestions() {
  if (!state.analysis) {
    return;
  }
  state.codingQuestionsVisible = !state.codingQuestionsVisible;
  renderInterviewPage();
}

function updateScoreLine(labelElement, barElement, value, max) {
  if (!max) {
    labelElement.textContent = "Not weighted";
    barElement.style.width = "0%";
    return;
  }
  labelElement.textContent = `${formatNumber(value)}/${formatNumber(max)}`;
  barElement.style.width = `${Math.max(0, Math.min(100, (value / max) * 100))}%`;
}

function renderInsights(insights, warnings) {
  const riskList = insights.risk_flags || [];
  const warningList = warnings || [];
  const combinedNotes = [...warningList, ...riskList];

  return `
    <div class="insight-grid">
      <section class="insight-card insight-card-strengths">
        <h3><span class="insight-icon">&#10003;</span><span>Strengths</span></h3>
        <ul>${renderListItems(insights.strengths, "No strengths were generated.")}</ul>
      </section>
      <section class="insight-card insight-card-weaknesses">
        <h3><span class="insight-icon">!</span><span>Weaknesses</span></h3>
        <ul>${renderListItems(insights.weaknesses, "No weaknesses were generated.")}</ul>
      </section>
    </div>
    ${
      combinedNotes.length
        ? `
          <section class="review-note-box">
            <h4>Review Notes</h4>
            <ul>${combinedNotes.map((item) => `<li>${item}</li>`).join("")}</ul>
          </section>
        `
        : ""
    }
  `;
}

function renderSkills(skillAnalysis, skillBuckets) {
  if (skillBuckets && (skillBuckets.relevant_skills?.length || skillBuckets.other_skills?.length)) {
    const rel = skillBuckets.relevant_skills || [];
    const other = skillBuckets.other_skills || [];
    return `
      <div class="skills-grid">
        <section class="skill-card">
          <h3>Relevant skills</h3>
          <div class="skill-chip-group">
            ${
              rel.length
                ? rel.map((name) => `<span class="skill-chip skill-chip-primary">${escapeHtml(name)}</span>`).join("")
                : `<p class="empty-copy">No direct role matches detected.</p>`
            }
          </div>
        </section>
        <section class="skill-card">
          <h3>Other skills</h3>
          <div class="skill-chip-group">
            ${
              other.length
                ? other.map((name) => `<span class="skill-chip skill-chip-secondary">${escapeHtml(name)}</span>`).join("")
                : `<p class="empty-copy">No additional skills listed beyond the role focus.</p>`
            }
          </div>
        </section>
      </div>
    `;
  }

  const primarySkills = skillAnalysis.primary_skills || [];
  const secondarySkills = skillAnalysis.secondary_skills || [];

  return `
    <div class="skills-grid">
      <section class="skill-card">
        <h3>Relevant skills</h3>
        <div class="skill-chip-group">
          ${
            primarySkills.length
              ? primarySkills
                  .map((skill) => `<span class="skill-chip skill-chip-primary">${skill.name} - ${skill.depth}</span>`)
                  .join("")
              : `<p class="empty-copy">No role-matched skills detected.</p>`
          }
        </div>
      </section>
      <section class="skill-card">
        <h3>Other skills</h3>
        <div class="skill-chip-group">
          ${
            secondarySkills.length
              ? secondarySkills.map((skill) => `<span class="skill-chip skill-chip-secondary">${skill.name}</span>`).join("")
              : `<p class="empty-copy">No secondary skills detected.</p>`
          }
        </div>
      </section>
    </div>
  `;
}

function renderQuestions(questions) {
  if (!questions.length) {
    return `<p class="empty-copy">No interview questions were generated for this resume.</p>`;
  }

  return `
    <div class="question-stack">
      ${questions
        .map((question, index) => {
          const category = inferQuestionCategory(question);
          const why = question.why_this_question
            ? escapeHtml(question.why_this_question)
            : "Grounded in the candidate's resume projects.";
          return `
            <article class="question-card">
              <div class="question-header">
                <h3>Q${index + 1}: ${escapeHtml(question.question)}</h3>
                <span class="difficulty-badge ${difficultyClass(question.difficulty)}">${escapeHtml(question.difficulty)}</span>
              </div>
              <p class="question-category"><strong>Category:</strong> ${escapeHtml(category)}</p>
              <div class="expected-answer-box">
                <span class="expected-answer-label">Expected Answer:</span>
                <p>${escapeHtml(question.expected_answer)}</p>
              </div>
              <p class="question-why"><strong>Why this question:</strong> ${why}</p>
            </article>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderProjects(projects) {
  if (!projects.length) {
    return `<p class="empty-copy">No project evidence was extracted from the uploaded resume.</p>`;
  }

  return `
    <div class="project-stack">
      ${projects
        .map(
          (project) => `
            <article class="project-card">
              <h3>${project.title}</h3>
              <p>${project.summary}</p>
              <div class="tech-chip-group">
                ${
                  project.technologies.length
                    ? project.technologies.map((item) => `<span class="tech-chip">${item}</span>`).join("")
                    : `<span class="tech-chip">No explicit technologies detected</span>`
                }
              </div>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderCodingQuestions(questions) {
  if (!questions.length) {
    return `<div class="coding-question-card"><p>No coding question is available for this profile.</p></div>`;
  }

  return questions
    .map(
      (question, index) => `
        <article class="coding-question-card">
          <h3>Coding Question ${index + 1}</h3>
          <p><strong>${question.skill_target}:</strong> ${question.prompt}</p>
          <p><strong>Expected Answer:</strong> ${question.expected_answer}</p>
        </article>
      `
    )
    .join("");
}

function renderPreparedQuestions(questions) {
  if (!questions.length) {
    return `<p class="empty-copy">No prepared questions are available.</p>`;
  }

  return questions
    .map((question) => {
      const category = inferQuestionCategory(question);
      const why = question.why_this_question
        ? `<p class="prepared-question-why"><strong>Why this question:</strong> ${escapeHtml(question.why_this_question)}</p>`
        : "";
      return `
        <article class="prepared-question-item">
          <div class="prepared-question-bar"></div>
          <div class="prepared-question-content">
            <h3>${escapeHtml(question.question)}</h3>
            <p>Category: ${escapeHtml(category)}</p>
            ${why}
          </div>
          <div class="prepared-question-badge">
            <span class="difficulty-badge ${difficultyClass(question.difficulty)}">${escapeHtml(question.difficulty)}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function setActiveTab(tab) {
  state.activeTab = tab;
  for (const button of tabButtons) {
    button.classList.toggle("active", button.dataset.tab === tab);
  }
  for (const panel of document.querySelectorAll(".analysis-panel")) {
    panel.classList.toggle("active", panel.id === `tab-${tab}`);
  }
}

function goToDashboard() {
  if (!state.analysis) {
    setCriteriaMessage("No dashboard is available yet. Complete a resume analysis first.", true);
    if (state.view !== "criteria") {
      setView("criteria");
    }
    return;
  }
  setView("analysis");
  setAnalysisMessage("Showing the most recent candidate analysis.");
}

function startInterview() {
  if (!state.analysis?.questions?.length) {
    setAnalysisMessage("Interview questions are not available for this candidate.", true);
    return;
  }
  state.interviewQuestionIndex = 0;
  state.codingQuestionsVisible = false;
  state.interviewSuggestionVisible = false;
  elements.interviewAction.value = "next question";
  elements.interviewContext.value = "";
  if (elements.interviewCommandInput) {
    elements.interviewCommandInput.value = "";
  }
  renderInterviewPage();
  setView("interview");
  setInterviewMessage("Interview mode ready. Use the copilot controls to guide the conversation.");
}

function toggleAssistant() {
  if (state.assistantOpen) {
    closeAssistant();
    return;
  }
  openAssistant();
}

function openAssistant() {
  state.assistantOpen = true;
  if (!state.assistantMessages.length) {
    pushAssistantMessage("assistant", buildAssistantWelcomeMessage());
  }
  renderAssistant();
  elements.assistantInput.focus();
}

function closeAssistant() {
  state.assistantOpen = false;
  renderAssistant();
}

function renderAssistant() {
  elements.assistantWidget.classList.toggle("is-open", state.assistantOpen);
  elements.chatFab.setAttribute("aria-expanded", state.assistantOpen ? "true" : "false");
  elements.assistantContextLine.textContent = getAssistantContextLine();
  elements.assistantInput.disabled = state.assistantLoading;
  elements.assistantSendBtn.disabled = state.assistantLoading;
  elements.assistantQuickActions.innerHTML = getAssistantQuickQuestions()
    .map((question) => `<button type="button" class="assistant-quick-chip" data-question="${escapeHtml(question)}">${escapeHtml(question)}</button>`)
    .join("");
  const messageMarkup = state.assistantMessages.length
    ? state.assistantMessages
        .map((message) => {
          const roleClass = message.role === "user" ? "user" : "assistant";
          const bubbleClass = message.role === "user" ? "chat-bubble-user" : "chat-bubble-ai";
          return `
            <div class="assistant-message-row ${roleClass}">
              <div class="chat-bubble ${bubbleClass}">${escapeHtml(message.text)}</div>
            </div>
          `;
        })
        .join("")
    : "";
  const loadingMarkup = state.assistantLoading
    ? `
      <div class="assistant-message-row assistant">
        <div class="chat-bubble chat-bubble-ai">Thinking with Ollama...</div>
      </div>
    `
    : "";
  elements.assistantThread.innerHTML = `${messageMarkup}${loadingMarkup}`;

  if (state.assistantOpen) {
    elements.assistantThread.scrollTop = elements.assistantThread.scrollHeight;
  }
}

async function handleAssistantSubmit(event) {
  event.preventDefault();
  const question = elements.assistantInput.value.trim();
  if (!question) {
    return;
  }
  await submitAssistantQuestion(question);
}

async function submitAssistantQuestion(question) {
  const cleanedQuestion = question.trim();
  if (!cleanedQuestion || state.assistantLoading) {
    return;
  }

  state.assistantOpen = true;
  pushAssistantMessage("user", cleanedQuestion);
  elements.assistantInput.value = "";
  state.assistantLoading = true;
  renderAssistant();

  try {
    const result = await requestAssistantReply(cleanedQuestion);
    pushAssistantMessage("assistant", result.answer);
  } catch (error) {
    pushAssistantMessage(
      "assistant",
      `I couldn't get a response from the Ollama assistant. ${error.message}`
    );
  } finally {
    state.assistantLoading = false;
    renderAssistant();
    elements.assistantInput.focus();
  }
}

async function requestAssistantReply(question) {
  const response = await fetch("/assistant/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildAssistantPayload(question)),
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.detail || result.answer || "The assistant request failed.");
  }
  return result;
}

function buildAssistantPayload(question) {
  const hasValidJobContext = state.jobContext.role && state.jobContext.role.trim().length >= 2;
  return {
    question,
    view: state.view,
    active_tab: state.activeTab,
    job_context: hasValidJobContext ? state.jobContext : null,
    analysis: state.analysis,
    history: state.assistantMessages
      .slice(0, -1)
      .slice(-8)
      .map((message) => ({
        role: message.role,
        content: message.text,
      })),
  };
}

function pushAssistantMessage(role, text) {
  state.assistantMessages.push({ role, text });
  if (state.assistantMessages.length > 24) {
    state.assistantMessages = state.assistantMessages.slice(-24);
  }
}

function buildAssistantWelcomeMessage() {
  return `Hi, I'm your AI Assistant. ${assistantCurrentScreenResponse()} You can ask me about the score, skills, strengths, projects, interview questions, coding test, or what to do next.`;
}

function getAssistantContextLine() {
  if (state.view === "criteria") {
    return "Ask about the hiring criteria, scoring model, or what to enter next.";
  }
  if (state.view === "upload") {
    return "Ask about resume upload, supported files, or what happens after analysis.";
  }
  if (state.view === "interview") {
    return "Ask about interview questions, risks to probe, coding prompts, or next interview steps.";
  }
  return "Ask about the score, matched skills, strengths, projects, recommendation, or next steps.";
}

function getAssistantQuickQuestions() {
  if (state.view === "criteria") {
    return [
      "What should I enter here?",
      "How are candidates scored?",
      "What can this agent do?",
    ];
  }
  if (state.view === "upload") {
    return [
      "What file types can I upload?",
      "What happens after upload?",
      "What should I do next?",
    ];
  }
  if (state.view === "interview") {
    return [
      "What should I ask next?",
      "Summarize the risks",
      "Show me the coding test focus",
    ];
  }
  return [
    "Summarize this candidate",
    "Explain the score",
    "What should I ask in the interview?",
  ];
}

function buildAssistantReply(question) {
  const normalized = question.trim().toLowerCase();

  if (normalized === "hi" || includesAny(normalized, ["hello", "hey", "good morning", "good evening"])) {
    return buildAssistantWelcomeMessage();
  }
  if (includesAny(normalized, ["what can you do", "help", "assist", "agent"])) {
    return assistantCapabilityResponse();
  }
  if (includesAny(normalized, ["this screen", "this page", "where am i", "what am i looking at", "current screen"])) {
    return assistantCurrentScreenResponse();
  }
  if (includesAny(normalized, ["next step", "what should i do next", "what now", "how do i continue"])) {
    return assistantNextStepResponse();
  }
  if (includesAny(normalized, ["job role", "required skills", "experience level", "hiring criteria", "criteria"])) {
    return assistantRoleResponse();
  }
  if (includesAny(normalized, ["upload", "resume", "file type", "pdf", "docx", "parser"])) {
    return assistantResumeResponse();
  }
  if (!state.analysis && includesAny(normalized, ["score", "candidate", "skill", "strength", "weakness", "project", "interview", "coding"])) {
    return noAnalysisResponse();
  }
  if (includesAny(normalized, ["skill", "matched", "missing", "primary", "secondary"])) {
    return assistantSkillsResponse(normalized);
  }
  if (includesAny(normalized, ["strength", "weakness", "risk", "concern"])) {
    return assistantInsightsResponse(normalized);
  }
  if (includesAny(normalized, ["project"])) {
    return assistantProjectsResponse();
  }
  if (includesAny(normalized, ["interview", "question", "ask next", "probe"])) {
    return assistantInterviewResponse(normalized);
  }
  if (includesAny(normalized, ["coding", "code test", "programming"])) {
    return assistantCodingResponse();
  }
  if (includesAny(normalized, ["score", "recommendation", "confidence", "hold", "hire", "reject", "why"])) {
    return assistantScoreResponse(normalized);
  }
  if (includesAny(normalized, ["summarize", "summary"])) {
    return state.analysis ? assistantCandidateSummaryResponse() : assistantCurrentScreenResponse();
  }

  return assistantFallbackResponse();
}

function assistantCapabilityResponse() {
  const base = [
    "I can explain the current screen and guide you through the next action.",
    "I can answer questions about the hiring criteria, upload flow, candidate score, recommendation, skills, strengths, weaknesses, projects, interview questions, and coding test.",
  ];
  if (state.analysis) {
    base.push(`For this candidate, I already have context on the score, recommendation, matched skills, and interview prompts.`);
  }
  return base.join(" ");
}

function assistantCurrentScreenResponse() {
  if (state.view === "criteria") {
    const skills = state.jobContext.required_skills.length
      ? ` Current required skills: ${formatInlineList(state.jobContext.required_skills, "none yet")}.`
      : "";
    const role = state.jobContext.role ? ` Current role: ${state.jobContext.role}.` : "";
    return `You are on the hiring criteria screen. Set the role, experience level, and required skills before continuing to resume upload.${role}${skills}`;
  }
  if (state.view === "upload") {
    return "You are on the resume upload screen. Upload a PDF or DOCX resume, then click Upload and Analyze so the system can extract evidence and build the candidate report.";
  }
  if (state.view === "interview") {
    return "You are on the interview copilot screen. This page gives you adaptive interview help, quick reference notes, coding-test prompts, and the prepared project-based questions.";
  }
  return "You are on the candidate analysis screen. This page shows the candidate profile, overall score, recommendation, and tabs for insights, skills, interview questions, and projects.";
}

function assistantNextStepResponse() {
  if (state.view === "criteria") {
    return "Next, enter the target role, choose the experience level, add the required skills, and continue to the resume upload step.";
  }
  if (state.view === "upload") {
    return "Next, upload the candidate resume and run the analysis. Once that completes, you can review the score, skills, and interview questions.";
  }
  if (state.view === "interview") {
    return "Next, use the prepared questions or ask the copilot for a suggestion, then probe the candidate on missing skills, project ownership, and any flagged risks.";
  }
  if (!state.analysis) {
    return "Next, complete a resume analysis so I can answer candidate-specific questions.";
  }
  return "Next, review the recommendation, inspect matched versus missing skills, then start the interview to validate the candidate's depth on projects and weaker areas.";
}

function assistantRoleResponse() {
  const role = state.jobContext.role || "not set yet";
  const experienceLevel = state.jobContext.experience_level || "Experienced";
  const requiredSkills = state.jobContext.required_skills.length
    ? formatInlineList(state.jobContext.required_skills, "none yet")
    : "none yet";
  return `The current job setup is role: ${role}, experience level: ${experienceLevel}, and required skills: ${requiredSkills}. This context drives skill matching, role alignment, question generation, and the final recommendation.`;
}

function assistantResumeResponse() {
  if (state.view === "upload") {
    return "This step accepts PDF and DOCX resumes. After upload, the system extracts candidate data, validates it, scores role fit, generates interview questions, and prepares the final recommendation.";
  }
  return "The resume upload step accepts PDF and DOCX files. After upload, the system parses the resume, extracts structured candidate data, scores role fit, and generates interview-ready outputs.";
}

function noAnalysisResponse() {
  return "I don't have candidate results yet. Complete the hiring criteria and upload a resume first, then I can explain the score, skills, strengths, projects, and interview questions.";
}

function assistantCandidateSummaryResponse() {
  const candidate = state.analysis.candidate;
  const finalDecision = state.analysis.final_decision;
  const scoreBreakdown = state.analysis.score_breakdown;
  return `${candidate.name || "This candidate"} is being evaluated for ${state.jobContext.role || "the selected role"}. The current result is ${Math.round(scoreBreakdown.final_score)}/100 with a ${finalDecision.recommendation} recommendation and ${finalDecision.confidence} confidence. Matched skills: ${formatInlineList(scoreBreakdown.matched_skills, "none")}. Missing skills: ${formatInlineList(scoreBreakdown.missing_skills, "none")}.`;
}

function assistantScoreResponse(question) {
  if (!state.analysis) {
    const weights = currentScoringWeights();
    return `Scoring is deterministic. For the current ${state.jobContext.experience_level.toLowerCase()} setup, weights are skills ${formatNumber(weights.skills)}%, projects ${formatNumber(weights.projects)}%, and experience ${formatNumber(weights.experience)}%.`;
  }

  const scoreBreakdown = state.analysis.score_breakdown;
  const finalDecision = state.analysis.final_decision;
  const confidence = state.analysis.confidence;
  const weights = scoreBreakdown.weights || currentScoringWeights();
  const weightedSkill = weightedPoints(scoreBreakdown.skill_score, weights.skills || 0);
  const weightedProject = weightedPoints(scoreBreakdown.project_score, weights.projects || 0);
  const weightedExperience = weightedPoints(scoreBreakdown.experience_score, weights.experience || 0);

  if (includesAny(question, ["confidence"])) {
    const label = confidence.confidence_label || confidence.band;
    const pct = confidence.confidence_score ?? confidence.score;
    return `Confidence is ${label} at ${formatNumber(pct)}/100. ${confidence.explanation}`;
  }
  if (includesAny(question, ["recommendation", "hold", "hire", "reject", "why"])) {
    return `${finalDecision.explanation}${finalDecision.overridden_by_hr ? ` HR override reason: ${finalDecision.override_reason || "not provided"}.` : ""}`;
  }

  return `The current score is ${formatNumber(scoreBreakdown.final_score)}/100. Weighted contribution is skills ${formatNumber(weightedSkill)}/${formatNumber(weights.skills || 0)}, projects ${formatNumber(weightedProject)}/${formatNumber(weights.projects || 0)}, and experience ${formatNumber(weightedExperience)}/${formatNumber(weights.experience || 0)}. ${scoreBreakdown.score_explanation.join(" ")}`;
}

function assistantSkillsResponse(question) {
  if (!state.analysis) {
    return noAnalysisResponse();
  }

  const scoreBreakdown = state.analysis.score_breakdown;
  const primarySkills = state.analysis.skill_analysis.primary_skills || [];
  const secondarySkills = state.analysis.skill_analysis.secondary_skills || [];

  if (includesAny(question, ["missing"])) {
    return `Missing skills for this role: ${formatInlineList(scoreBreakdown.missing_skills, "none detected")}.`;
  }
  if (includesAny(question, ["matched"])) {
    return `Matched skills for this role: ${formatInlineList(scoreBreakdown.matched_skills, "none detected")}.`;
  }
  if (includesAny(question, ["primary"])) {
    return primarySkills.length
      ? `Primary skills are ${primarySkills.map((skill) => `${skill.name} (${skill.depth}, confidence ${formatNumber(skill.confidence)})`).join(", ")}.`
      : "No primary skills were detected for the selected role.";
  }
  if (includesAny(question, ["secondary"])) {
    return secondarySkills.length
      ? `Secondary skills are ${secondarySkills.map((skill) => skill.name).join(", ")}.`
      : "No secondary skills were extracted from the resume.";
  }

  return `Matched skills: ${formatInlineList(scoreBreakdown.matched_skills, "none")}. Missing skills: ${formatInlineList(scoreBreakdown.missing_skills, "none")}. Primary strengths to validate in the interview: ${primarySkills.length ? primarySkills.slice(0, 3).map((skill) => `${skill.name} (${skill.depth})`).join(", ") : "none yet"}.`;
}

function assistantInsightsResponse(question) {
  if (!state.analysis) {
    return noAnalysisResponse();
  }

  const insights = state.analysis.insights;
  const warnings = state.analysis.warnings || [];
  const riskFlags = [...(insights.risk_flags || []), ...warnings];

  if (includesAny(question, ["strength"])) {
    return `Top strengths: ${formatInlineList(insights.strengths, "none")}.`;
  }
  if (includesAny(question, ["weakness"])) {
    return `Top weaknesses: ${formatInlineList(insights.weaknesses, "none")}.`;
  }
  return `Main risks and review notes: ${formatInlineList(riskFlags, "no additional risk flags")}.`;
}

function assistantProjectsResponse() {
  if (!state.analysis) {
    return noAnalysisResponse();
  }

  const projects = state.analysis.candidate.projects || [];
  if (!projects.length) {
    return "No project evidence was extracted from the resume, so project-based validation will be limited.";
  }

  return projects
    .slice(0, 3)
    .map((project, index) => `${index === 0 ? "Projects:" : ""} ${project.title} uses ${formatInlineList(project.technologies, "no explicit technologies listed")} and is described as ${project.summary}`)
    .join(" ");
}

function assistantInterviewResponse(question) {
  if (!state.analysis) {
    return noAnalysisResponse();
  }

  const questions = state.analysis.questions || [];
  if (!questions.length) {
    return "Interview questions are not available yet for this candidate.";
  }

  if (includesAny(question, ["ask next", "next"])) {
    const nextQuestion = questions[state.interviewQuestionIndex] || questions[0];
    return `A good next question is: ${nextQuestion.question} Expected answer direction: ${nextQuestion.expected_answer}`;
  }

  return `Prepared interview focus: ${questions.slice(0, 3).map((item, index) => `Q${index + 1}: ${item.question}`).join(" ")} Use these to validate project ownership and role-matched skills.`;
}

function assistantCodingResponse() {
  if (!state.analysis) {
    return noAnalysisResponse();
  }

  const codingQuestions = state.analysis.coding_assessment.questions || [];
  if (!codingQuestions.length) {
    return "There is no coding test generated for this candidate yet.";
  }

  return `Coding test focus: ${codingQuestions.map((question) => `${question.skill_target}: ${question.prompt}`).join(" ")}`;
}

function assistantFallbackResponse() {
  if (!state.analysis) {
    return `${assistantCurrentScreenResponse()} I can also explain the scoring model, upload flow, and how this agent will evaluate candidates once a resume is analyzed.`;
  }

  return `I can help with this candidate's score, recommendation, matched and missing skills, strengths, weaknesses, projects, interview questions, coding test, or the best next step from the ${state.view} screen.`;
}

function parseSkills(input) {
  return input
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function openFilePicker() {
  elements.resumeFileInput.value = "";
  elements.resumeFileInput.click();
}

function weightedPoints(rawScore, weight) {
  if (!weight) {
    return 0;
  }
  return (Number(rawScore) * Number(weight)) / 100;
}

function formatRecommendation(recommendation) {
  if (recommendation === "Hold") {
    return "Hold - Further Evaluation";
  }
  return recommendation;
}

function recommendationClass(recommendation) {
  return recommendation.toLowerCase();
}

function difficultyClass(difficulty) {
  return `difficulty-${difficulty.toLowerCase()}`;
}

function inferQuestionCategory(question) {
  const knownSkills = state.analysis?.candidate?.skills || [];
  const matchedSkill = knownSkills.find((skill) => question.question.toLowerCase().includes(skill.toLowerCase()));
  return matchedSkill || question.project_name;
}

function selectedActionLabel() {
  return elements.interviewAction.options[elements.interviewAction.selectedIndex]?.text || "Agent Action";
}

function renderListItems(items, fallback) {
  if (!items.length) {
    return `<li>${fallback}</li>`;
  }
  return items.map((item) => `<li>${item}</li>`).join("");
}

function formatNumber(value) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return "--";
  }
  return Number.isInteger(parsed) ? `${parsed}` : parsed.toFixed(2).replace(/\.?0+$/, "");
}

function currentScoringWeights() {
  return state.jobContext.experience_level === "Fresher"
    ? { skills: 50, projects: 50, experience: 0 }
    : { skills: 40, projects: 30, experience: 30 };
}

function formatInlineList(items, fallback) {
  return items && items.length ? items.join(", ") : fallback;
}

function includesAny(text, candidates) {
  return candidates.some((candidate) => text.includes(candidate));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setCriteriaMessage(message, isError = false) {
  updateMessage(elements.criteriaMessage, message, isError);
}

function setUploadMessage(message, isError = false) {
  updateMessage(elements.uploadMessage, message, isError);
}

function setAnalysisMessage(message, isError = false) {
  updateMessage(elements.analysisMessage, message, isError);
}

function setInterviewMessage(message, isError = false) {
  updateMessage(elements.interviewMessage, message, isError);
}

function updateMessage(element, message, isError) {
  element.textContent = message;
  element.classList.toggle("is-error", Boolean(message) && isError);
}
