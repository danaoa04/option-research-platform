import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./app/App";
import "./theme/app.css";
import "./theme/strategy.css";
import "./theme/research.css";

const root=document.getElementById("root");
if(!root)throw new Error("Application root is missing");
ReactDOM.createRoot(root).render(<React.StrictMode><BrowserRouter><App/></BrowserRouter></React.StrictMode>);
