import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./app/App";
import { Providers } from "./app/providers";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <Providers>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </Providers>
  </React.StrictMode>,
);

