import { DECISIONS, RISK_RULES } from "../content.js";

export default function RiskRules() {
  return (
    <>
      <h3 className="rules-title">The risk rules</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rule</th>
              <th>When</th>
              <th>Points</th>
            </tr>
          </thead>
          <tbody>
            {RISK_RULES.map((row) => (
              <tr key={row.rule}>
                <td>{row.rule}</td>
                <td>{row.when}</td>
                <td className="pts">+{row.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="decisions">
        {DECISIONS.map((decision) => (
          <span key={decision.label} className="pill">
            <i style={{ background: decision.color }}></i>
            {decision.label}
          </span>
        ))}
      </div>
    </>
  );
}
