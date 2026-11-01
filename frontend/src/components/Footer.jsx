import { DEMO_WARNING } from "../content.js";

// The site links to a public demo API: the warning must always be visible.
export default function Footer() {
  return (
    <footer>
      <div className="container">
        <span>{DEMO_WARNING}</span>
      </div>
    </footer>
  );
}
