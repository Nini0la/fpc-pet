export type PowerItem={id:string;title:string;reason:string;kind:string;score:number};
export type TodayData={
  local_date:string;
  briefing:{content:string;local_date:string}|null;
  power_list:PowerItem[];
  open_commitments:{id:string;title:string;deadline_hint?:string|null}[];
  resurfaced_items:{id:string;title:string}[];
  evening_reflection:{status:"not_started"|"awaiting"|"completed";journal:unknown|null};
};

export default function Today({data}:{data:TodayData}){
  return <section aria-labelledby="today-heading">
    <h2 id="today-heading">Today</h2>
    <time>{data.local_date}</time>
    {data.briefing&&<p>{data.briefing.content}</p>}
    {data.power_list.length>0&&<section><h3>Power List</h3><ol>{data.power_list.map(item=><li key={item.id}><strong>{item.title}</strong><small>{item.reason}</small></li>)}</ol></section>}
    {data.open_commitments.length>0&&<section><h3>Open commitments</h3><ul>{data.open_commitments.map(item=><li key={item.id}>{item.title}{item.deadline_hint?` — ${item.deadline_hint}`:""}</li>)}</ul></section>}
    {data.resurfaced_items.length>0&&<section><h3>Resurfaced</h3><ul>{data.resurfaced_items.map(item=><li key={item.id}>{item.title}</li>)}</ul></section>}
    <p>Evening reflection: {data.evening_reflection.status}</p>
  </section>;
}
