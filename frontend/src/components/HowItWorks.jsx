import { STEPS } from "../content.js";
import RiskRules from "./RiskRules.jsx";

export default function HowItWorks() {
  return (
    <section id="how">
      <div className="container">
        <h2>How a transaction is decided</h2>
        <p className="sub">Every request passes the same steps, all inside the customer network.</p>
        <div className="grid">
          {STEPS.map((step, index) => (
            <div key={step.title} className="card">
              <span className="step">{String(index + 1).padStart(2, "0")}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </div>
          ))}
        </div>
        <RiskRules />
      </div>
    </section>
  );
}
