import type { ButtonHTMLAttributes, PropsWithChildren, ReactNode } from "react";

export function Button({ children, ...props }: PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>>) {
  return <button className="button" {...props}>{children}</button>;
}
export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}
export function Card({ title, children, action }: PropsWithChildren<{ title: string; action?: ReactNode }>) {
  return <section className="card"><header><h2>{title}</h2>{action}</header>{children}</section>;
}
export function Metric({ label, value, tone = "neutral" }: { label: string; value: ReactNode; tone?: string }) {
  return <div className={`metric metric--${tone}`}><span>{label}</span><strong>{value}</strong></div>;
}
export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty"><strong>{title}</strong><p>{detail}</p></div>;
}
