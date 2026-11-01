import { NAV } from "../content.js";

export default function Header() {
  return (
    <header>
      <nav className="nav container">
        <a className="brand" href="#top">
          <img src="/assets/emblem.png" alt="" width="80" height="40" />
          <span>
            Veloce <b>AI</b>
          </span>
        </a>
        <div className="links">
          {NAV.map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </div>
      </nav>
    </header>
  );
}
