"use client";

import {FormEvent,useEffect,useState} from "react";
import Chat,{type Message} from "./chat";
import Today,{type TodayData} from "./today";
import VocabularyHistory,{type VocabularyHistoryItem} from "./vocabulary-history";

const API=process.env.NEXT_PUBLIC_API_URL??"http://localhost:8000";

async function fetchMessages():Promise<Message[]>{
  const response=await fetch(`${API}/api/chat/messages`,{credentials:"include"});
  if(!response.ok) throw new Error("Not authenticated");
  return response.json();
}
async function fetchToday():Promise<TodayData>{
  const response=await fetch(`${API}/api/today`,{credentials:"include"});
  if(!response.ok) throw new Error("Unable to load Today");
  return response.json();
}
async function fetchVocabulary():Promise<VocabularyHistoryItem[]>{
  const response=await fetch(`${API}/api/vocabulary?limit=20&offset=0`,{credentials:"include"});
  if(!response.ok) throw new Error("Unable to load vocabulary history");
  return (await response.json()).items;
}

export default function Page(){
  const [ready,setReady]=useState(false);
  const [messages,setMessages]=useState<Message[]>([]);
  const [today,setToday]=useState<TodayData|null>(null);
  const [vocabulary,setVocabulary]=useState<VocabularyHistoryItem[]>([]);
  const [code,setCode]=useState("");

  useEffect(()=>{
    fetchMessages().then(async history=>{
      setMessages(history);
      setToday(await fetchToday());
      setVocabulary(await fetchVocabulary());
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
      setToday(await fetchToday());
      setVocabulary(await fetchVocabulary());
      setReady(true);
    }
  }

  if(ready) return <><Today data={today!}/><VocabularyHistory items={vocabulary}/><Chat initialMessages={messages}/></>;
  return <main><h1>Continuity</h1><form onSubmit={login}><label htmlFor="code">Access code</label><input id="code" type="password" value={code} onChange={e=>setCode(e.target.value)}/><button>Sign in</button></form></main>;
}
