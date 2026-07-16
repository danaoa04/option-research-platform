import type{CompatibilityResult}from"../api/compatibility";import type{RuntimeConfig,RuntimeMode}from"../config/runtime";
export interface DiagnosticEvent{at:string;level:"error"|"warn"|"info";category:string;message:string;requestId?:string}
const events:DiagnosticEvent[]=[];const secretPattern=/(api[-_]?key|token|secret|password|credential)=?[^\s,]*/gi;
export function redact(value:string){return value.replace(secretPattern,"$1=[REDACTED]").replace(/\/(Users|home)\/[^/\s]+/g,"/$1/[REDACTED]")}
export function logDiagnostic(event:Omit<DiagnosticEvent,"at">){events.push({...event,message:redact(event.message),at:new Date().toISOString()});if(events.length>100)events.shift()}
export function recentDiagnostics(){return structuredClone(events)}
export function createDiagnosticBundle(config:RuntimeConfig,mode:RuntimeMode,compatibility:CompatibilityResult){return{schemaVersion:1,generatedAt:new Date().toISOString(),frontend:{version:"0.1.0",build:"sprint-11f-local"},runtime:{mode,apiVersion:config.apiVersion,backendBaseUrl:redact(config.backendBaseUrl),fixtureMode:config.fixtureMode,tauriMode:config.tauriMode,webglNodeLimit:config.webglNodeLimit},compatibility,capabilities:{webgl:detectWebGL(),storage:typeof localStorage!=="undefined",networkPolicy:"local backend only"},events:recentDiagnostics()}}
export function detectWebGL(){if(typeof navigator!=="undefined"&&navigator.userAgent.includes("jsdom"))return false;try{const canvas=document.createElement("canvas");return Boolean(canvas.getContext("webgl2")||canvas.getContext("webgl"))}catch{return false}}
