import { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [documentId, setDocumentId] = useState("4");
  const [findings, setFindings] = useState([]);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadFindings = async () => {
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API}/findings/${documentId}`
      );

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

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API}/documents/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.error || "Upload failed"
        );
      }

      setDocumentId(String(data.document_id));
      setFile(null);
      setMessage(
        `Uploaded ${data.filename} successfully. Document ID: ${data.document_id}`
      );

      await loadFindingsForDocument(data.document_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const loadFindingsForDocument = async (id) => {
    setLoading(true);

    try {
      const response = await fetch(
        `${API}/findings/${id}`
      );

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

  const reviewFinding = async (id, decision) => {
    try {
      const response = await fetch(
        `${API}/findings/${id}/review`,
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
        <h1>HyperDoc</h1>
        <p>Agentic Document Review</p>
      </header>

      <main className="container">

        <section className="upload-panel">
          <h2>Upload Document</h2>
          <p>Upload a PDF, DOCX, or TXT document for analysis.</p>

          <div className="upload-row">
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) =>
                setFile(e.target.files[0] || null)
              }
            />

            <button
              type="button"
              onClick={uploadDocument}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "Upload"}
            </button>
          </div>
        </section>

        {message && (
          <p className="success">
            {message}
          </p>
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
          >
            Load Findings
          </button>
        </div>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Review Findings</h2>
              <p>
                AI-detected conflicts requiring human review.
              </p>
            </div>

            <span className="count">
              {findings.length} findings
            </span>
          </div>

          {loading && <p>Loading findings...</p>}

          {error && (
            <p className="error">
              {error}
            </p>
          )}

          {!loading &&
            !error &&
            findings.length === 0 && (
              <div className="empty">
                No findings for this document.
              </div>
            )}

          {findings.map((finding) => (
            <div
              className="finding"
              key={finding.id}
            >
              <div className="finding-content">
                <div className="top-row">
                  <span className="badge">
                    {finding.type}
                  </span>

                  <span
                    className={`status ${finding.status}`}
                  >
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
                    type="button"
                    className="accept"
                    onClick={() =>
                      reviewFinding(
                        finding.id,
                        "accepted"
                      )
                    }
                  >
                    Accept
                  </button>

                  <button
                    type="button"
                    className="reject"
                    onClick={() =>
                      reviewFinding(
                        finding.id,
                        "rejected"
                      )
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