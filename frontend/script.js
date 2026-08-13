/* =====================================================
   DATAGUARD AI
   Frontend Controller
===================================================== */


/* =====================================================
   CONFIGURATION
===================================================== */

const API_BASE_URL = "http://127.0.0.1:8000";


/* =====================================================
   DOM ELEMENTS
===================================================== */

const fileInput =
    document.getElementById("fileInput");

const browseButton =
    document.getElementById("browseButton");

const dropZone =
    document.getElementById("dropZone");

const selectedFile =
    document.getElementById("selectedFile");

const selectedFileName =
    document.getElementById("selectedFileName");

const analyzeButton =
    document.getElementById("analyzeButton");

const loadingState =
    document.getElementById("loadingState");

const loadingTitle =
    document.getElementById("loadingTitle");

const loadingText =
    document.getElementById("loadingText");

const errorMessage =
    document.getElementById("errorMessage");

const resultsSection =
    document.getElementById("resultsSection");

const analysisContent =
    document.getElementById("analysisContent");

const analysisFileName =
    document.getElementById("analysisFileName");

const analysisTime =
    document.getElementById("analysisTime");

const similarIncidents =
    document.getElementById("similarIncidents");

const chatMessages =
    document.getElementById("chatMessages");

const chatInput =
    document.getElementById("chatInput");

const chatSendButton =
    document.getElementById("chatSendButton");

const newAnalysisButton =
    document.getElementById("newAnalysisButton");

const systemStatus =
    document.getElementById("systemStatus");


/* =====================================================
   STATE
===================================================== */

let currentFile = null;

let currentIncidentContext = null;

let isAnalyzing = false;

let isChatting = false;


/* =====================================================
   INITIALIZATION
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        checkBackend();

    }
);


/* =====================================================
   BACKEND HEALTH CHECK
===================================================== */

async function checkBackend() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/health`
            );


        if (!response.ok) {

            throw new Error(
                "Backend unavailable"
            );

        }


        const data =
            await response.json();


        if (
            data.status === "healthy"
        ) {

            systemStatus.textContent =
                "System Ready";

        } else {

            systemStatus.textContent =
                "Backend Issue";

        }

    } catch (error) {

        systemStatus.textContent =
            "Backend Offline";

        console.warn(
            "Backend health check failed:",
            error
        );

    }

}


/* =====================================================
   BROWSE FILE
===================================================== */

browseButton.addEventListener(
    "click",
    () => {

        fileInput.click();

    }
);


/* =====================================================
   FILE INPUT
===================================================== */

fileInput.addEventListener(
    "change",
    event => {

        const file =
            event.target.files[0];


        if (file) {

            handleFile(file);

        }

    }
);


/* =====================================================
   HANDLE FILE
===================================================== */

function handleFile(file) {

    hideError();


    const allowedTypes = [
        ".txt",
        ".pdf",
        ".docx"
    ];


    const fileName =
        file.name.toLowerCase();


    const isValid =
        allowedTypes.some(
            extension =>
                fileName.endsWith(extension)
        );


    if (!isValid) {

        showError(
            "Please upload a TXT, PDF or DOCX file."
        );

        return;

    }


    currentFile = file;


    selectedFileName.textContent =
        `📄 ${file.name}`;


    selectedFile.classList.remove(
        "hidden"
    );


    analyzeButton.disabled =
        false;


    systemStatus.textContent =
        "File Ready";

}


/* =====================================================
   DRAG & DROP
===================================================== */

dropZone.addEventListener(
    "dragover",
    event => {

        event.preventDefault();

        dropZone.classList.add(
            "drag-over"
        );

    }
);


dropZone.addEventListener(
    "dragleave",
    () => {

        dropZone.classList.remove(
            "drag-over"
        );

    }
);


dropZone.addEventListener(
    "drop",
    event => {

        event.preventDefault();

        dropZone.classList.remove(
            "drag-over"
        );


        const file =
            event.dataTransfer.files[0];


        if (file) {

            handleFile(file);

        }

    }
);


/* =====================================================
   ANALYZE BUTTON
===================================================== */

analyzeButton.addEventListener(
    "click",
    analyzeIncident
);


/* =====================================================
   ANALYZE INCIDENT
===================================================== */

async function analyzeIncident() {

    if (!currentFile) {

        showError(
            "Please select an incident report first."
        );

        return;

    }


    if (isAnalyzing) {

        return;

    }


    isAnalyzing = true;


    hideError();

    setLoading(true);


    const startTime =
        performance.now();


    try {

        const formData =
            new FormData();


        formData.append(
            "file",
            currentFile
        );


        updateLoading(
            "Reading incident report...",
            "Extracting production incident details."
        );


        await sleep(150);


        updateLoading(
            "Searching incident history...",
            "Comparing the incident against 160 historical cases."
        );


        const response =
            await fetch(
                `${API_BASE_URL}/analyze`,
                {
                    method: "POST",
                    body: formData
                }
            );


        if (!response.ok) {

            let message =
                "Incident analysis failed.";


            try {

                const errorData =
                    await response.json();


                if (
                    errorData.detail
                ) {

                    message =
                        extractChatText(
                            errorData.detail
                        );

                }

            } catch (_) {}


            throw new Error(
                message
            );

        }


        updateLoading(
            "AI is investigating...",
            "Combining RAG evidence with Gemini reasoning."
        );


        const data =
            await response.json();


        const endTime =
            performance.now();


        const totalSeconds =
            (
                endTime -
                startTime
            ) / 1000;


        /*
         * Save complete backend response
         * for the chatbot.
         */

        currentIncidentContext =
            data;


        renderAnalysis(
            data
        );


        renderSimilarIncidents(
            data
        );


        analysisFileName.textContent =
            currentFile.name;


        analysisTime.textContent =
            `Completed in ${totalSeconds.toFixed(1)}s`;


        enableChat();


        resultsSection.classList.remove(
            "hidden"
        );


        setLoading(false);


        setTimeout(
            () => {

                resultsSection.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });

            },
            100
        );


        systemStatus.textContent =
            "Analysis Complete";


    } catch (error) {

        console.error(
            "Analysis error:",
            error
        );


        setLoading(false);


        showError(
            error.message ||
            "Something went wrong while analyzing the incident."
        );


        systemStatus.textContent =
            "Analysis Failed";


    } finally {

        isAnalyzing = false;

    }

}


/* =====================================================
   RENDER AI ANALYSIS
===================================================== */

function renderAnalysis(data) {

    const answer =
        data.answer ||
        data.analysis ||
        data.result ||
        data.response ||
        "";


    analysisContent.innerHTML =
        formatAIResponse(
            extractChatText(answer)
        );

}


/* =====================================================
   FORMAT GEMINI RESPONSE
===================================================== */

function formatAIResponse(text) {

    if (!text) {

        return `
            <p>
                No AI analysis was returned.
            </p>
        `;

    }


    let html =
        escapeHTML(
            text
        );


    /*
     * Markdown headings
     */

    html =
        html.replace(
            /^### (.*?)$/gm,
            "<h3>$1</h3>"
        );


    html =
        html.replace(
            /^## (.*?)$/gm,
            "<h3>$1</h3>"
        );


    html =
        html.replace(
            /^# (.*?)$/gm,
            "<h3>$1</h3>"
        );


    /*
     * Bold text
     */

    html =
        html.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );


    /*
     * Bullet points
     */

    html =
        html.replace(
            /^[-*]\s+(.*?)$/gm,
            "<li>$1</li>"
        );


    /*
     * Numbered points
     */

    html =
        html.replace(
            /^\d+\.\s+(.*?)$/gm,
            "<li>$1</li>"
        );


    /*
     * Group consecutive list items
     */

    html =
        html.replace(
            /((?:<li>.*?<\/li>\s*)+)/gs,
            "<ul>$1</ul>"
        );


    /*
     * Paragraphs
     */

    const blocks =
        html.split(
            /\n\s*\n/
        );


    let output = "";


    blocks.forEach(
        block => {

            block =
                block.trim();


            if (!block) {

                return;

            }


            if (
                block.startsWith("<h3>") ||
                block.startsWith("<ul>")
            ) {

                output +=
                    block;

            } else {

                output +=
                    `<p>${block.replace(
                        /\n/g,
                        " "
                    )}</p>`;

            }

        }
    );


    return output;

}


/* =====================================================
   RENDER RAG INCIDENTS
===================================================== */

function renderSimilarIncidents(data) {

    similarIncidents.innerHTML =
        "";


    /*
     * Support different backend
     * response names.
     */

    const incidents =
        data.top_incidents ||
        data.similar_incidents ||
        data.retrieved_incidents ||
        data.incidents ||
        [];


    if (
        !Array.isArray(incidents) ||
        incidents.length === 0
    ) {

        similarIncidents.innerHTML = `

            <div class="incident-card">

                <div class="incident-description">

                    No historical incidents
                    were returned.

                </div>

            </div>

        `;

        return;

    }


    incidents
        .slice(0, 3)
        .forEach(
            (incident, index) => {

                const card =
                    createIncidentCard(
                        incident,
                        index
                    );


                similarIncidents.appendChild(
                    card
                );

            }
        );

}


/* =====================================================
   CREATE RAG CARD
===================================================== */

function createIncidentCard(
    incident,
    index
) {

    const card =
        document.createElement(
            "div"
        );


    card.className =
        "incident-card";


    const incidentId =
        incident.incident_id ||
        incident.id ||
        `INC-${String(
            index + 1
        ).padStart(
            3,
            "0"
        )}`;


    const similarity =
        incident.similarity ??
        incident.score ??
        incident.distance ??
        0;


    const type =
        incident.anomaly_type ||
        incident.type ||
        incident.anomaly?.type ||
        "Unknown";


    const description =
        incident.description ||
        incident.anomaly?.description ||
        "Historical production incident";


    const severity =
        incident.severity ||
        incident.anomaly?.severity ||
        "Unknown";


    const rootCause =
        incident.root_cause?.description ||
        incident.rootCause?.description ||
        incident.root_cause ||
        incident.rootCause ||
        "Historical root cause available";


    let percentage =
        "—";


    if (
        typeof similarity === "number"
    ) {

        percentage =
            (
                similarity * 100
            ).toFixed(1);

    }


    card.innerHTML = `

        <div class="incident-card-top">

            <div class="incident-id">
                ${escapeHTML(
                    String(incidentId)
                )}
            </div>

            <div class="similarity-badge">
                ${percentage}% MATCH
            </div>

        </div>


        <div class="incident-type">

            ${escapeHTML(
                String(type)
            )}

        </div>


        <div class="incident-description">

            ${escapeHTML(
                String(description)
            )}

        </div>


        <div class="incident-details">

            <div class="incident-detail">

                <span>
                    Severity
                </span>

                <span>
                    ${escapeHTML(
                        String(severity)
                    )}
                </span>

            </div>


            <div class="incident-detail">

                <span>
                    Root Cause
                </span>

                <span>
                    ${escapeHTML(
                        truncate(
                            String(rootCause),
                            70
                        )
                    )}
                </span>

            </div>

        </div>

    `;


    return card;

}


/* =====================================================
   CHAT
===================================================== */

chatSendButton.addEventListener(
    "click",
    sendChatMessage
);


chatInput.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendChatMessage();

        }

    }
);


/* =====================================================
   ENABLE CHAT
===================================================== */

function enableChat() {

    chatInput.disabled =
        false;


    chatSendButton.disabled =
        false;


    chatInput.placeholder =
        "Ask DataGuard AI about this incident...";

}


/* =====================================================
   SEND CHAT MESSAGE
===================================================== */

async function sendChatMessage() {

    if (
        isChatting ||
        !currentIncidentContext
    ) {

        return;

    }


    const question =
        chatInput.value.trim();


    if (!question) {

        return;

    }


    isChatting = true;


    /*
     * Show user message immediately.
     */

    addChatMessage(
        question,
        "user"
    );


    chatInput.value =
        "";


    chatInput.disabled =
        true;


    chatSendButton.disabled =
        true;


    const thinkingId =
        addThinkingMessage();


    try {

        /*
         * Send question + current
         * incident context to FastAPI.
         */

        const response = await fetch("http://127.0.0.1:8000/chat", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        question: question,
        incident: currentIncidentContext.current_incident,
        similar_incidents:
            currentIncidentContext.similar_incidents || []
    })
});


        /*
         * HTTP error
         */

        if (!response.ok) {

            let errorText =
                "Chat request failed.";


            try {

                const errorData =
                    await response.json();


                console.error(
                    "Chat backend error:",
                    errorData
                );


                if (
                    errorData.detail
                ) {

                    errorText =
                        extractChatText(
                            errorData.detail
                        );

                }

            } catch (_) {}


            throw new Error(
                errorText
            );

        }


        /*
         * Read JSON response.
         */

        const data =
            await response.json();


        /*
         * IMPORTANT:
         *
         * This lets us see the exact
         * backend response in DevTools.
         */

        console.log(
            "CHAT RESPONSE:",
            data
        );


        removeThinkingMessage(
            thinkingId
        );


        /*
         * Backend can return:
         *
         * {
         *   "answer": "..."
         * }
         *
         * OR
         *
         * {
         *   "response": "..."
         * }
         *
         * OR
         *
         * {
         *   "message": "..."
         * }
         *
         * OR nested objects/arrays.
         */

        let answer =
            data.answer ??
            data.response ??
            data.message ??
            data.result ??
            data.output ??
            data.content;


        /*
         * Convert the response into
         * readable text.
         *
         * This specifically fixes:
         *
         * [object Object],[object Object]
         */

        answer =
            extractChatText(
                answer
            );


        if (!answer) {

            answer =
                "I received a response, but there was no readable answer.";

        }


        /*
         * Display AI response.
         */

        addChatMessage(
            answer,
            "assistant"
        );


    } catch (error) {

        console.error(
            "Chat error:",
            error
        );


        removeThinkingMessage(
            thinkingId
        );


        const readableError =
            extractChatText(
                error.message
            );


        addChatMessage(
            `Sorry, I couldn't process that question. ${readableError}`,
            "assistant"
        );


    } finally {

        isChatting = false;


        chatInput.disabled =
            false;


        chatSendButton.disabled =
            false;


        chatInput.focus();

    }

}


/* =====================================================
   EXTRACT CHAT TEXT
===================================================== */

/*
 * This is the important fix.
 *
 * It handles:
 *
 * String
 * Array
 * Object
 * Nested Object
 * Gemini-style responses
 *
 * instead of displaying:
 *
 * [object Object]
 */

function extractChatText(value) {

    /*
     * Nothing returned.
     */

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    /*
     * Normal string.
     */

    if (
        typeof value === "string"
    ) {

        return value;

    }


    /*
     * Number / boolean.
     */

    if (
        typeof value === "number" ||
        typeof value === "boolean"
    ) {

        return String(
            value
        );

    }


    /*
     * Array.
     *
     * Example:
     *
     * [
     *   { text: "Hello" },
     *   { text: "How can I help?" }
     * ]
     */

    if (
        Array.isArray(value)
    ) {

        return value
            .map(
                item =>
                    extractChatText(
                        item
                    )
            )
            .filter(
                Boolean
            )
            .join(
                "\n\n"
            );

    }


    /*
     * Object.
     */

    if (
        typeof value === "object"
    ) {

        /*
         * Common response fields.
         */

        const possibleFields = [

            "answer",

            "response",

            "message",

            "text",

            "content",

            "result",

            "output",

            "generated_text",

            "reply"

        ];


        /*
         * Search those fields first.
         */

        for (
            const field
            of possibleFields
        ) {

            if (
                value[field] !==
                    undefined &&
                value[field] !==
                    null
            ) {

                const extracted =
                    extractChatText(
                        value[field]
                    );


                if (
                    extracted
                ) {

                    return extracted;

                }

            }

        }


        /*
         * Gemini-style structure:
         *
         * {
         *   candidates: [
         *      {
         *        content: {
         *          parts: [
         *             { text: "..." }
         *          ]
         *        }
         *      }
         *   ]
         * }
         */

        if (
            value.candidates
        ) {

            const extracted =
                extractChatText(
                    value.candidates
                );


            if (
                extracted
            ) {

                return extracted;

            }

        }


        /*
         * Gemini content object.
         */

        if (
            value.parts
        ) {

            const extracted =
                extractChatText(
                    value.parts
                );


            if (
                extracted
            ) {

                return extracted;

            }

        }


        /*
         * If no known field exists,
         * recursively inspect the object.
         */

        const values =
            Object.values(
                value
            );


        const extractedValues =
            values
                .map(
                    item =>
                        extractChatText(
                            item
                        )
                )
                .filter(
                    Boolean
                );


        if (
            extractedValues.length > 0
        ) {

            return extractedValues.join(
                "\n\n"
            );

        }


        /*
         * Final fallback.
         *
         * Never allow [object Object].
         */

        try {

            return JSON.stringify(
                value,
                null,
                2
            );

        } catch (_) {

            return String(
                value
            );

        }

    }


    return String(
        value
    );

}


/* =====================================================
   ADD CHAT MESSAGE
===================================================== */

function addChatMessage(
    text,
    type
) {

    const wrapper =
        document.createElement(
            "div"
        );


    wrapper.className =
        `chat-message ${type}`;


    const avatar =
        document.createElement(
            "div"
        );


    avatar.className =
        "message-avatar";


    avatar.textContent =
        type === "assistant"
            ? "✦"
            : "You";


    const content =
        document.createElement(
            "div"
        );


    content.className =
        "message-content";


    const name =
        document.createElement(
            "strong"
        );


    name.textContent =
        type === "assistant"
            ? "DataGuard AI"
            : "You";


    const message =
        document.createElement(
            "p"
        );


    if (
        type === "assistant"
    ) {

        message.innerHTML =
            formatChatResponse(
                extractChatText(
                    text
                )
            );

    } else {

        message.textContent =
            extractChatText(
                text
            );

    }


    content.appendChild(
        name
    );


    content.appendChild(
        message
    );


    wrapper.appendChild(
        avatar
    );


    wrapper.appendChild(
        content
    );


    chatMessages.appendChild(
        wrapper
    );


    scrollChatToBottom();

}


/* =====================================================
   FORMAT CHAT RESPONSE
===================================================== */

function formatChatResponse(
    text
) {

    let html =
        escapeHTML(
            String(text)
        );


    /*
     * Bold markdown.
     */

    html =
        html.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );


    /*
     * Inline code.
     */

    html =
        html.replace(
            /`([^`]+)`/g,
            "<code>$1</code>"
        );


    /*
     * Convert newlines.
     */

    html =
        html.replace(
            /\n/g,
            "<br>"
        );


    return html;

}


/* =====================================================
   THINKING MESSAGE
===================================================== */

function addThinkingMessage() {

    const id =
        `thinking-${Date.now()}`;


    const wrapper =
        document.createElement(
            "div"
        );


    wrapper.className =
        "chat-message assistant";


    wrapper.id =
        id;


    wrapper.innerHTML = `

        <div class="message-avatar">
            ✦
        </div>

        <div class="message-content">

            <strong>
                DataGuard AI
            </strong>

            <p>
                Thinking...
            </p>

        </div>

    `;


    chatMessages.appendChild(
        wrapper
    );


    scrollChatToBottom();


    return id;

}


/* =====================================================
   REMOVE THINKING MESSAGE
===================================================== */

function removeThinkingMessage(
    id
) {

    const element =
        document.getElementById(
            id
        );


    if (element) {

        element.remove();

    }

}


/* =====================================================
   NEW ANALYSIS
===================================================== */

newAnalysisButton.addEventListener(
    "click",
    resetApplication
);


function resetApplication() {

    currentFile =
        null;


    currentIncidentContext =
        null;


    isAnalyzing =
        false;


    isChatting =
        false;


    fileInput.value =
        "";


    selectedFile.classList.add(
        "hidden"
    );


    selectedFileName.textContent =
        "";


    analyzeButton.disabled =
        true;


    resultsSection.classList.add(
        "hidden"
    );


    analysisContent.innerHTML =
        "";


    similarIncidents.innerHTML =
        "";


    chatMessages.innerHTML = `

        <div class="chat-message assistant">

            <div class="message-avatar">
                ✦
            </div>

            <div class="message-content">

                <strong>
                    DataGuard AI
                </strong>

                <p>
                    I've analyzed your incident.
                    Ask me anything about the diagnosis,
                    evidence, resolution or prevention.
                </p>

            </div>

        </div>

    `;


    chatInput.value =
        "";


    chatInput.disabled =
        true;


    chatSendButton.disabled =
        true;


    hideError();


    setLoading(
        false
    );


    systemStatus.textContent =
        "System Ready";


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

}


/* =====================================================
   LOADING
===================================================== */

function setLoading(
    visible
) {

    if (visible) {

        loadingState.classList.remove(
            "hidden"
        );


        analyzeButton.disabled =
            true;

    } else {

        loadingState.classList.add(
            "hidden"
        );


        analyzeButton.disabled =
            !currentFile;

    }

}


function updateLoading(
    title,
    text
) {

    loadingTitle.textContent =
        title;


    loadingText.textContent =
        text;

}


/* =====================================================
   ERROR
===================================================== */

function showError(
    message
) {

    errorMessage.textContent =
        extractChatText(
            message
        );


    errorMessage.classList.remove(
        "hidden"
    );

}


function hideError() {

    errorMessage.classList.add(
        "hidden"
    );


    errorMessage.textContent =
        "";

}


/* =====================================================
   CHAT SCROLL
===================================================== */

function scrollChatToBottom() {

    chatMessages.scrollTop =
        chatMessages.scrollHeight;

}


/* =====================================================
   ESCAPE HTML
===================================================== */

function escapeHTML(
    value
) {

    return String(
        value
    )
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}


/* =====================================================
   TRUNCATE
===================================================== */

function truncate(
    text,
    maxLength
) {

    if (
        text.length <=
        maxLength
    ) {

        return text;

    }


    return (
        text.substring(
            0,
            maxLength
        ) +
        "..."
    );

}


/* =====================================================
   SLEEP
===================================================== */

function sleep(
    ms
) {

    return new Promise(
        resolve =>
            setTimeout(
                resolve,
                ms
            )
    );

}