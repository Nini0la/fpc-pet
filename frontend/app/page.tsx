"use client";

import {FormEvent,useEffect,useState} from "react";
import Chat,{type Message} from "./chat";

const API=process.env.NEXT_PUBLIC_API_URL??"http://localhost:8000";

async function fetchMessages():Promise<Message[]>{
  const response=await fetch(`${API}/api/chat/messages`,{credentials:"include"});
  if(!response.ok) throw new Error("Not authenticated");
  return response.json();
}

export default function Page(){
  const [ready,setReady]=useState(false);
  const [messages,setMessages]=useState<Message[]>([]);
  const [code,setCode]=useState("");

  useEffect(()=>{
    fetchMessages().then(history=>{
      setMessages(history);
      setReady(true);
    }).catch(()=>undefined);
  },[]);

  async function login(e:FormEvent){
    e.preventDefault();
    const response=await fetch(`${API}/api/auth/login`,{
      method:"POST",
      credentials:"include",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({access_code:code,username:"owner"}),
    });
    if(response.ok){
      const history=await fetchMessages();
      setMessages(history);
      setReady(true);
    }
  }

  if(ready) return <Chat initialMessages={messages}/>;
  return <main><h1>Continuity</h1><form onSubmit={login}><label htmlFor="code">Access code</label><input id="code" type="password" value={code} onChange={e=>setCode(e.target.value)}/><button>Sign in</button></form></main>;
}
