"use client";
import {FormEvent,useEffect,useRef,useState} from "react";
import {api,ApiError} from "./api";
export type Message={id:string;role:"user"|"assistant";content:string;created_at?:string;proactive?:boolean};
type Pending={content:string;eventId:string;accepted:boolean};
const EMPTY_MESSAGES:Message[]=[];

export default function Chat({initialMessages=EMPTY_MESSAGES,onSessionExpired=()=>undefined,onChanged=()=>undefined}:{initialMessages?:Message[];onSessionExpired?:()=>void;onChanged?:()=>void}){
  const [messages,setMessages]=useState(initialMessages);const [text,setText]=useState("");const [sending,setSending]=useState(false);const [error,setError]=useState("");const [pending,setPending]=useState<Pending|null>(null);const inputRef=useRef<HTMLTextAreaElement>(null);
  // Parent data is authoritative after reconciliation and scheduled actions.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(()=>setMessages(initialMessages),[initialMessages]);
  async function deliver(content:string,retry:Pending|null=null){
    const trimmed=content.trim();if(!trimmed||sending)return;const attempt=retry??{content:trimmed,eventId:crypto.randomUUID(),accepted:false};
    if(!retry){setMessages(all=>[...all,{id:`pending-${attempt.eventId}`,role:"user",content:trimmed,created_at:new Date().toISOString()}]);setText("");}
    setSending(true);setError("");setPending(attempt);
    try{
      if(!attempt.accepted){await api("/api/chat/messages",{method:"POST",body:JSON.stringify({content:attempt.content,event_id:attempt.eventId})});attempt.accepted=true;setPending({...attempt});}
      const history=await api<Message[]>("/api/chat/messages?limit=100");setMessages(history);setPending(null);onChanged();
    }catch(cause){
      if(cause instanceof ApiError&&cause.status===401){setError("Your session expired. Sign in again to continue.");onSessionExpired();}
      else setError(attempt.accepted?"Message accepted, but conversation refresh failed. Retry to reconcile safely.":"Delivery is uncertain. Retry safely with the same event ID.");
    }finally{setSending(false)}
  }
  function send(event:FormEvent){event.preventDefault();void deliver(text)}
  return <section className="view chat-view" aria-labelledby="chat-heading"><header className="view-header"><div><span className="eyebrow">A shared conversation</span><h1 id="chat-heading">Chat</h1><p>Talk naturally. Continuity only retains explicit, useful details.</p></div></header>
    <div className="messages" aria-live="polite" aria-busy={sending}>{messages.length===0?<div className="empty"><h2>Start where you are</h2><p>Share a plan, a commitment, or something you want to think through.</p></div>:messages.map(message=><article className={`message ${message.role}`} key={message.id}><header><span>{message.role==="assistant"?"Continuity":"You"}</span>{message.proactive&&<span className="badge">Proactive</span>}</header><p>{message.content}</p>{message.created_at&&<time dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}</time>}</article>)}</div>
    {error&&<div className="error-row" role="alert"><span>{error}</span>{pending&&<button className="secondary" onClick={()=>deliver(pending.content,pending)}>Retry</button>}</div>}
    <form className="composer" onSubmit={send}><label htmlFor="message" className="visually-hidden">Message</label><textarea ref={inputRef} id="message" maxLength={4000} rows={3} value={text} onChange={event=>setText(event.target.value)} placeholder="Message Continuity…"/><div><small>{text.length} / 4000</small><button disabled={sending||!text.trim()}>{sending?"Sending…":"Send"}</button></div></form>
  </section>;
}
