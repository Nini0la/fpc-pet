"use client";
import {FormEvent,useState} from "react";
import {api,ApiError} from "./api";
export type Message={id:string;role:"user"|"assistant";content:string;created_at?:string;proactive?:boolean};

export default function Chat({initialMessages=[],onSessionExpired=()=>undefined}:{initialMessages?:Message[];onSessionExpired?:()=>void}){
  const [messages,setMessages]=useState(initialMessages);const [text,setText]=useState("");const [sending,setSending]=useState(false);const [error,setError]=useState("");const [retryText,setRetryText]=useState("");
  async function deliver(content:string){
    const trimmed=content.trim();if(!trimmed||sending)return;const eventId=crypto.randomUUID();const optimistic:Message={id:`pending-${eventId}`,role:"user",content:trimmed,created_at:new Date().toISOString()};
    setMessages(all=>[...all,optimistic]);setText("");setSending(true);setError("");setRetryText(trimmed);
    try{await api("/api/chat/messages",{method:"POST",body:JSON.stringify({content:trimmed,event_id:eventId})});const history=await api<Message[]>("/api/chat/messages");setMessages(history);setRetryText("");}
    catch(cause){setMessages(all=>all.filter(item=>item.id!==optimistic.id));if(cause instanceof ApiError&&cause.status===401){setError("Your session expired. Sign in again to continue.");onSessionExpired();}else setError("Your message was not sent. Check your connection and try again.");}
    finally{setSending(false)}
  }
  function send(event:FormEvent){event.preventDefault();void deliver(text)}
  return <section className="view chat-view" aria-labelledby="chat-heading"><header className="view-header"><div><span className="eyebrow">A shared conversation</span><h1 id="chat-heading">Chat</h1><p>Talk naturally. Continuity only retains explicit, useful details.</p></div></header>
    <div className="messages" aria-live="polite" aria-busy={sending}>{messages.length===0?<div className="empty"><h2>Start where you are</h2><p>Share a plan, a commitment, or something you want to think through.</p></div>:messages.map(message=><article className={`message ${message.role}`} key={message.id}><header><span>{message.role==="assistant"?"Continuity":"You"}</span>{message.proactive&&<span className="badge">Proactive</span>}</header><p>{message.content}</p>{message.created_at&&<time dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}</time>}</article>)}</div>
    {error&&<div className="error-row" role="alert"><span>{error}</span>{retryText&&<button className="secondary" onClick={()=>deliver(retryText)}>Retry</button>}</div>}
    <form className="composer" onSubmit={send}><label htmlFor="message" className="visually-hidden">Message</label><textarea id="message" maxLength={4000} rows={3} value={text} onChange={event=>setText(event.target.value)} placeholder="Message Continuity…"/><div><small>{text.length} / 4000</small><button disabled={sending||!text.trim()}>{sending?"Sending…":"Send"}</button></div></form>
  </section>;
}
