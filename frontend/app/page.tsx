"use client";

import { FormEvent, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Source = {
  source_document: string;
  section_title: string;
  collection: string;
  headings: string[];
};

type ChatResponse = {
  answer: string;
  sources: Source[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [username, setUsername] = useState("dr.mehta");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const result = await fetch(`${apiBaseUrl}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!result.ok) {
      setError("Unable to sign in with those credentials.");
      return;
    }
    const data = await result.json();
    setToken(data.access_token);
    setRole(data.role);
  }

  async function askQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !question.trim()) return;
    setLoading(true);
    setError("");
    const result = await fetch(`${apiBaseUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ question }),
    });
    setLoading(false);
    if (!result.ok) {
      const data = await result.json().catch(() => null);
      setError(
        typeof data?.detail === "string"
          ? data.detail
          : "MediBot could not process that question yet.",
      );
      return;
    }
    setResponse(await result.json());
  }

  return (
    <main className="shell">
      <section className="intro">
        <p className="eyebrow">MEDIASSIST / KNOWLEDGE DESK</p>
        <h1>Ask with confidence.</h1>
        <p className="lede">
          A role-aware workspace for finding the right clinical, operational,
          and billing guidance.
        </p>
        <div className="signal-row">
          <span className="signal-dot" />
          <span>
            {role ? `Signed in as ${role}` : "Secure session required"}
          </span>
        </div>
      </section>

      <section className="workspace" aria-label="MediBot workspace">
        {!token ? (
          <form className="panel login-panel" onSubmit={login}>
            <div>
              <p className="panel-kicker">IDENTITY CHECK</p>
              <h2>Sign in to continue</h2>
              <p className="muted">
                Your role controls which knowledge collections can answer.
              </p>
            </div>
            <label>
              Username
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button type="submit">
              Open workspace <span aria-hidden="true">-&gt;</span>
            </button>
          </form>
        ) : (
          <form className="panel question-panel" onSubmit={askQuestion}>
            <div className="panel-heading">
              <div>
                <p className="panel-kicker">LIVE CONSULTATION</p>
                <h2>What do you need to know?</h2>
              </div>
              <span className="role-badge">{role}</span>
            </div>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about policy, procedures, clinical guidance, or authorized claims data..."
              rows={5}
            />
            <div className="action-row">
              <span className="muted">
                Answers are grounded in authorized sources.
              </span>
              <button type="submit" disabled={loading}>
                {loading ? "Thinking..." : "Ask MediBot"}
              </button>
            </div>
          </form>
        )}

        {response && (
          <section className="panel answer-panel">
            <p className="panel-kicker">MEDIBOT RESPONSE</p>
            <div className="answer">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ node: _node, ...props }) => (
                    <a {...props} target="_blank" rel="noreferrer" />
                  ),
                }}
              >
                {response.answer}
              </ReactMarkdown>
            </div>
            {response.sources.length > 0 && (
              <div className="sources">
                <h3>Sources</h3>
                {response.sources.map((source, index) => (
                  <div
                    className="source"
                    key={`${source.source_document}-${source.section_title}-${source.headings.join("-")}-${index}`}
                  >
                    <strong>{source.source_document}</strong>
                    <span>
                      {source.headings.length > 0
                        ? source.headings.join(" / ")
                        : source.section_title === "Unknown"
                          ? "Document text"
                          : source.section_title}
                      {" / "}
                      {source.collection}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </section>
    </main>
  );
}
