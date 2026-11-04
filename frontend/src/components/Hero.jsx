import { HERO, LINKS } from "../content.js";

export default function Hero() {
  return (
    <div className="hero container">
      <div>
        <span className="badge">{HERO.badge}</span>
        <h1>{HERO.title}</h1>
        <p className="lead">{HERO.lead}</p>
        <div className="actions">
          <a className="btn btn-primary" href={LINKS.api}>
            Try the live API
          </a>
          <a className="btn btn-secondary" href={LINKS.code}>
            View the code
          </a>
        </div>
      </div>
      <img
        className="hero-logo"
        src="/assets/logo.png"
        alt="Veloce AI logo: a payment card protected by a shield"
        width="440"
        height="440"
      />
    </div>
  );
}
