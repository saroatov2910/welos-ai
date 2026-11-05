import { Fragment } from "react";
import { PIPELINE } from "../content.js";

export default function Pipeline() {
  return (
    <section id="pipeline" className="alt">
      <div className="container">
        <h2>Delivery pipeline</h2>
        <p className="sub">Every change is checked on the pull request, then checked again before it reaches Kubernetes. The Render demo and this website deploy separately from main.</p>
        <div className="pipeline">
          {PIPELINE.map((stage, index) => (
            <Fragment key={stage.label}>
              {index > 0 && (
                <span className="arrow" aria-hidden="true">
                  →
                </span>
              )}
              <span className={`chip ${stage.done ? "done" : "next"}`}>{stage.label}</span>
            </Fragment>
          ))}
        </div>
        <div className="legend">
          <span>
            <span className="chip done legend-swatch">&nbsp;</span> Running today
          </span>
          <span>
            <span className="chip next legend-swatch">&nbsp;</span> On the roadmap
          </span>
        </div>
      </div>
    </section>
  );
}
