import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [documentId, setDocumentId] = useState("4");
  const [findings, setFindings] = useState([]);
  const [file, setFile] = useState(null);
  const [rulesText, setRulesText] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [reviewing, setReviewing] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [agentResult, setAgentResult] = useState(null);

  const loadFindings = async () => {
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(`${API}/findings/${documentId}`);

      if (!response.ok) {
        throw new Error("Failed to load findings");
      }

      setFindings(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadFindingsForDocument = async (id) => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/findings/${id}`);

      if (!response.ok) {
        throw new Error("Failed to load findings");
      }

      setFindings(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const uploadDocument = async () => {
    if (!file) {
      setError("Please select a document first.");
      return;
    }

    setUploading(true);
    setError("");
    setMessage("");
    setAgentResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const uploadResponse = await fetch(
        `${API}/documents/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const uploadData = await uploadResponse.json();

      if (!uploadResponse.ok) {
        throw new Error(
          uploadData.detail ||
            uploadData.error ||
            "Upload failed"
        );
      }

      const id = uploadData.document_id;

      setDocumentId(String(id));
      setFile(null);

      setMessage(
        `Uploaded ${uploadData.filename}. Running document agent...`
      );

      const rules = rulesText
        .split("\n")
        .map((rule) => rule.trim())
        .filter(Boolean);

      const agentResponse = await fetch(
        `${API}/documents/agent/run`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            document_ids: [id],
            rules,
          }),
        }
      );

      const agentData = await agentResponse.json();

      if (!agentResponse.ok) {
        throw new Error(
          agentData.detail ||
            agentData.error ||
            "Document agent failed"
        );
      }

      setAgentResult(agentData);

      setMessage(
        `Analysis complete. ${agentData.finding_ids.length} finding(s) require review.`
      );

      await loadFindingsForDocument(id);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const reviewFinding = async (id, decision) => {
    setReviewing(id);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API}/findings/${id}/review`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            decision,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to review finding");
      }

      setMessage(
        `Finding #${id} marked as ${decision}.`
      );

      await loadFindings();
    } catch (err) {
      setError(err.message);
    } finally {
      setReviewing(null);
    }
  };

  useEffect(() => {
    loadFindings();
  }, []);

  return (
    <div className="app">
      <header className="header">
        <h1>HyperDoc</h1>
        <p>Agentic Document Review</p>
      </header>

      <main className="container">
        <section className="upload-panel">
          <h2>Upload Document</h2>

          <p>
            Upload a PDF, DOCX, or TXT document for analysis.
          </p>

          <div className="rules-section">
            <label htmlFor="rules">
              Review Rules / Checklist
            </label>

            <p className="rules-help">
              Add one rule per line. The agent will check
              the uploaded document against these rules.
            </p>

            <textarea
              id="rules"
              value={rulesText}
              onChange={(event) =>
                setRulesText(event.target.value)
              }
              placeholder={
                "Payment terms must be Net 30 days.\nThe contract must identify the vendor."
              }
              rows={4}
              disabled={uploading}
            />
          </div>

          <div className="upload-row">
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(event) =>
                setFile(event.target.files[0] || null)
              }
              disabled={uploading}
            />

            <button
              type="button"
              onClick={uploadDocument}
              disabled={uploading}
            >
              {uploading
                ? "Analyzing..."
                : "Upload & Analyze"}
            </button>
          </div>
        </section>

        {message && (
          <p className="success">
            {message}
          </p>
        )}

        {error && (
          <p className="error">
            {error}
          </p>
        )}

        {agentResult && (
          <section className="panel analysis-panel">
            <div className="panel-header">
              <div>
                <h2>Analysis Summary</h2>

                <p>
                  Document agent execution results.
                </p>
              </div>

              <span
                className={`status ${agentResult.status}`}
              >
                {agentResult.status}
              </span>
            </div>

            <div className="metrics">
              <div className="metric">
                <span>Run ID</span>
                <strong>
                  #{agentResult.run_id}
                </strong>
              </div>

              <div className="metric">
                <span>Facts</span>
                <strong>
                  {agentResult.extracted_fact_ids?.length ?? 0}
                </strong>
              </div>

              <div className="metric">
                <span>Findings</span>
                <strong>
                  {agentResult.finding_ids?.length ?? 0}
                </strong>
              </div>

              <div className="metric">
                <span>Duration</span>
                <strong>
                  {agentResult.total_duration_seconds}s
                </strong>
              </div>

              <div className="metric">
                <span>LLM Tokens</span>
                <strong>
                  {agentResult.llm_usage?.total_tokens ?? 0}
                </strong>
              </div>
            </div>

            {agentResult.rules?.length > 0 && (
              <div className="rules-result">
                <h3>Rules Checked</h3>

                <div className="rules-result-list">
                  {agentResult.rules.map(
                    (rule, index) => (
                      <div
                        className="rule-result"
                        key={`${rule}-${index}`}
                      >
                        <span className="rule-number">
                          {index + 1}
                        </span>

                        <span>{rule}</span>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            {agentResult.stage_timings && (
              <div className="pipeline">
                <h3>Pipeline Stages</h3>

                <div className="stage-list">
                  {Object.entries(
                    agentResult.stage_timings
                  ).map(([stage, duration]) => (
                    <div
                      className="stage"
                      key={stage}
                    >
                      <span>
                        {stage.replaceAll("_", " ")}
                      </span>

                      <strong>
                        {duration}s
                      </strong>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {agentResult.extracted_facts?.length > 0 && (
              <div className="facts-section">
                <h3>Extracted Facts</h3>

                <div className="facts-list">
                  {agentResult.extracted_facts.map(
                    (fact) => (
                      <div
                        className="fact-card"
                        key={fact.id}
                      >
                        <div className="fact-main">
                          <span className="fact-name">
                            {fact.fact}
                          </span>

                          <strong className="fact-value">
                            {fact.value}
                          </strong>
                        </div>

                        <div className="fact-source">
                          <span>
                            Document {fact.document_id}
                          </span>

                          <span>
                            Chunk {fact.chunk_id}
                          </span>

                          {fact.page_number !== null &&
                            fact.page_number !== undefined && (
                              <span>
                                Page {fact.page_number}
                              </span>
                            )}

                          {fact.section && (
                            <span>
                              Section: {fact.section}
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            {agentResult.draft && (
              <div className="draft">
                <h3>Generated Draft</h3>

                <div className="draft-content">
                  <ReactMarkdown>
                    {agentResult.draft}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </section>
        )}

        <div className="toolbar">
          <div className="input-group">
            <label htmlFor="document-id">
              Document ID
            </label>

            <input
              id="document-id"
              type="text"
              value={documentId}
              onChange={(event) =>
                setDocumentId(event.target.value)
              }
            />
          </div>

          <button
            type="button"
            onClick={loadFindings}
            disabled={loading}
          >
            {loading
              ? "Loading..."
              : "Load Findings"}
          </button>
        </div>

        <section className="panel findings-panel">
          <div className="panel-header">
            <div>
              <h2>Review Findings</h2>

              <p>
                AI-detected conflicts and rule violations
                requiring human review.
              </p>
            </div>

            <span className="count">
              {findings.length}{" "}
              {findings.length === 1
                ? "finding"
                : "findings"}
            </span>
          </div>

          {loading && (
            <div className="empty">
              Loading findings...
            </div>
          )}

          {!loading &&
            !error &&
            findings.length === 0 && (
              <div className="empty">
                No findings for this document.
              </div>
            )}

          {!loading &&
            findings.map((finding) => (
              <article
                className="finding"
                key={finding.id}
              >
                <div className="finding-content">
                  <div className="finding-header">
                    <div className="top-row">
                      <span
                        className={`badge ${
                          finding.type === "rule"
                            ? "rule"
                            : "conflict"
                        }`}
                      >
                        {finding.type || "CONFLICT"}
                      </span>

                      <span
                        className={`status ${finding.status}`}
                      >
                        {finding.status}
                      </span>
                    </div>

                    <span className="finding-number">
                      Finding #{finding.id}
                    </span>
                  </div>

                  <div className="finding-description">
                    <span className="finding-label">
                      {finding.type === "rule"
                        ? "Rule Check"
                        : "Conflict"}
                    </span>

                    <h3>
                      {finding.description}
                    </h3>
                  </div>
                </div>

                {finding.status === "pending" && (
                  <div className="actions">
                    <button
                      type="button"
                      className="accept"
                      disabled={
                        reviewing === finding.id
                      }
                      onClick={() =>
                        reviewFinding(
                          finding.id,
                          "accepted"
                        )
                      }
                    >
                      {reviewing === finding.id
                        ? "Saving..."
                        : "Accept"}
                    </button>

                    <button
                      type="button"
                      className="reject"
                      disabled={
                        reviewing === finding.id
                      }
                      onClick={() =>
                        reviewFinding(
                          finding.id,
                          "rejected"
                        )
                      }
                    >
                      {reviewing === finding.id
                        ? "Saving..."
                        : "Reject"}
                    </button>
                  </div>
                )}
              </article>
            ))}
        </section>
      </main>
    </div>
  );
}

export default App;