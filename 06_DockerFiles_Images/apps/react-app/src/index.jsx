import React from "react";
import { createRoot } from "react-dom/client";

function App() {
  return (
    <div>
      <h1>React app</h1>
      <p>Anshul Mohanty - 24BCS10191</p>
      <p>Bundled with esbuild, served by NGINX</p>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
