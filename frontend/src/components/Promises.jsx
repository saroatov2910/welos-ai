import { PROMISES } from "../content.js";
import Icon from "./Icon.jsx";

export default function Promises() {
  return (
    <section id="promises" className="alt">
      <div className="container">
        <h2>Five promises</h2>
        <p className="sub">What the product guarantees, and what each guarantee asks of the infrastructure.</p>
        <div className="grid">
          {PROMISES.map((promise) => (
            <div key={promise.title} className="card">
              <Icon name={promise.icon} />
              <h3>
                {promise.title} <span className={`status ${promise.status}`}>{promise.label}</span>
              </h3>
              <p>{promise.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
