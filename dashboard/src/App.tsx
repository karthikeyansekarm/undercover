import { useEffect, useState } from "react";
import { ClaimPage } from "./ClaimPage";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";

function useHash(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const update = () => {
      setHash(window.location.hash);
    };
    window.addEventListener("hashchange", update);
    return () => {
      window.removeEventListener("hashchange", update);
    };
  }, []);
  return hash;
}

function BackendStatus() {
  const [status, setStatus] = useState("checking");
  useEffect(() => {
    void fetch("/api/health")
      .then((response) => (response.ok ? "up" : "down"))
      .catch(() => "down")
      .then(setStatus);
  }, []);
  return <p className="muted">Backend: {status}</p>;
}

function Page({ hash }: Readonly<{ hash: string }>) {
  const claim = /^#\/claims\/(.+)$/.exec(hash);
  if (claim?.[1]) return <ClaimPage claimId={claim[1]} />;
  if (hash === "#/instructions") return <Instructions />;
  return <Queue />;
}

export function App() {
  const hash = useHash();
  return (
    <>
      <header className="top">
        <h1>
          <a href="#/">UnderCover</a>
        </h1>
        <p className="tagline">Claims, handled.</p>
        <nav>
          <a
            href="#/"
            aria-current={
              hash.startsWith("#/instructions") ? undefined : "page"
            }
          >
            Queue
          </a>
          <a
            href="#/instructions"
            aria-current={hash === "#/instructions" ? "page" : undefined}
          >
            Agent instructions
          </a>
        </nav>
      </header>
      <main>
        <Page hash={hash} />
      </main>
      <footer>
        <BackendStatus />
      </footer>
    </>
  );
}
