import type { OperationalAlert, ProviderJob, ProviderSummary } from "../types/providers";
import { demoAlerts, demoJobs, demoProviders } from "../fixtures/demo";

export class ApiError extends Error {
  constructor(message: string, readonly status?: number, readonly requestId?: string) { super(message); }
}
export interface ProviderApiClient {
  providers(signal?: AbortSignal): Promise<ProviderSummary[]>;
  jobs(signal?: AbortSignal): Promise<ProviderJob[]>;
  alerts(signal?: AbortSignal): Promise<OperationalAlert[]>;
  compatibility(signal?: AbortSignal): Promise<{ compatible: boolean; apiVersion: string; backend: string }>;
}
export interface ClientConfig { baseUrl: string; apiVersion: "v1"; timeoutMs: number; offlineDemo: boolean; }

const redact=(value:string)=>value.replace(/(api[_-]?key|token|secret)=([^&\s]+)/gi,"$1=***");
export function createProviderApiClient(config:ClientConfig):ProviderApiClient{
  async function read<T>(path:string,fixture:T,signal?:AbortSignal):Promise<T>{
    if(config.offlineDemo)return structuredClone(fixture);
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),config.timeoutMs);
    signal?.addEventListener("abort",()=>controller.abort(),{once:true});
    const requestId=crypto.randomUUID();
    try{const response=await fetch(`${config.baseUrl}/${config.apiVersion}${path}`,{headers:{"X-API-Version":config.apiVersion,"X-Request-ID":requestId},signal:controller.signal});if(!response.ok)throw new ApiError(redact(`Request failed: ${response.status}`),response.status,requestId);return await response.json() as T;}finally{clearTimeout(timer)}
  }
  return {providers:signal=>read("/providers",demoProviders,signal),jobs:signal=>read("/providers/jobs",demoJobs,signal),alerts:signal=>read("/providers/alerts",demoAlerts,signal),compatibility:signal=>read("/health",{compatible:true,apiVersion:"v1",backend:"offline-fixture"},signal)};
}
