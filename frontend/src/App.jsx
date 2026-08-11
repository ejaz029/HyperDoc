import { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [documentId, setDocumentId] = useState(4);
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadFindings = async () => {
    setLoading(true);
    setError("");

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

  const reviewFinding = async (findingId, decision) => {
    try {
      const response = await fetch(
        `${API}/findings/${findingId}/review`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ decision }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to review finding");
      }

      await loadFindings();
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadFindings();
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>HyperDoc</h1>
          <p>Agentic Document Review</p>
        </div>
      </header>

      <main className="container">
        <div className="toolbar">
          <div>
            <label>Document ID</label>
            <input
              type="text"
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
            />
          </div>

          <button onClick={loadFindings}>Load Findings</button>
        </div>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Review Findings</h2>
              <p>AI-detected conflicts requiring human review.</p>
            </div>

            <span className="count">
              {findings.length} findings
            </span>
          </div>

          {loading && <p>Loading findings...</p>}

          {error && <p className="error">{error}</p>}

          {!loading && !error && findings.length === 0 && (
            <div className="empty">
              No findings for this document.
            </div>
          )}

          {findings.map((finding) => (
            <div className="finding" key={finding.id}>
              <div className="finding-content">
                <div className="top-row">
                  <span className="badge">{finding.type}</span>

                  <span className={`status ${finding.status}`}>
                    {finding.status}
                  </span>
                </div>

                <h3>{finding.description}</h3>

                <p className="finding-id">
                  Finding #{finding.id}
                </p>
              </div>

              {finding.status === "pending" && (
                <div className="actions">
                  <button
                    className="accept"
                    onClick={() =>
                      reviewFinding(finding.id, "accepted")
                    }
                  >
                    Accept
                  </button>

                  <button
                    className="reject"
                    onClick={() =>
                      reviewFinding(finding.id, "rejected")
                    }
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}

export default App;