import Footer from "./components/Footer.jsx";
import Header from "./components/Header.jsx";
import Hero from "./components/Hero.jsx";
import HowItWorks from "./components/HowItWorks.jsx";
import Pipeline from "./components/Pipeline.jsx";
import Promises from "./components/Promises.jsx";

// The page, top to bottom. Every section is its own component in components/,
// and every text it shows lives in content.js.
export default function App() {
  return (
    <>
      <Header />
      <main id="top">
        <Hero />
        <Promises />
        <HowItWorks />
        <Pipeline />
      </main>
      <Footer />
    </>
  );
}
