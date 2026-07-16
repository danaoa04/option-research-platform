export type ThemeMode="system"|"light"|"dark";export type Density="compact"|"comfortable";
export interface Preferences{theme:ThemeMode;density:Density;reducedMotion:boolean;timezone:string;currency:string;offlineDemo:boolean}
const defaults:Preferences={theme:"system",density:"compact",reducedMotion:false,timezone:"Europe/London",currency:"USD",offlineDemo:true};
const KEY="orp-ui-preferences-v1";
export function loadPreferences():Preferences{try{const value=localStorage.getItem(KEY);if(!value)return defaults;const parsed=JSON.parse(value) as Partial<Preferences>;return{...defaults,...parsed,offlineDemo:parsed.offlineDemo??true};}catch{return defaults}}
export function savePreferences(value:Preferences):void{localStorage.setItem(KEY,JSON.stringify(value));document.documentElement.dataset.theme=value.theme;document.documentElement.dataset.density=value.density;}
