import {fireEvent,render,screen,waitFor,within} from "@testing-library/react";
import {afterEach,describe,expect,it,vi} from "vitest";
import Page from "../app/page";
import Threads,{type ThreadItem} from "../app/threads";
import History,{type TimelineItem} from "../app/history";

const emptyToday={local_date:"2026-10-01",briefing:null,vocabulary:null,power_list:[],open_commitments:[],active_threads:[],resurfaced_items:[],evening_reflection:{status:"not_started",journal:null}};
const prefs={timezone:"UTC",morning_time:"08:00",evening_time:"20:00",onboarding_complete:true,version:1};
function json(value:unknown,status=200){return new Response(JSON.stringify(value),{status,headers:{"content-type":"application/json"}})}

afterEach(()=>vi.restoreAllMocks());

describe("Milestone 5 shell",()=>{
  it("explains selective memory and privacy before access-code login",async()=>{
    vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(null,{status:401}));
    render(<Page/>);
    expect(await screen.findByRole("heading",{name:"Your days, carried forward"})).toBeInTheDocument();
    expect(screen.getByText(/selective memory/i)).toBeInTheDocument();
    expect(screen.getByText(/inspect, correct, or delete/i)).toBeInTheDocument();
    expect(screen.getByText(/retention/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Access code")).toHaveAttribute("autocomplete","current-password");
  });

  it("loads history after login and navigates among only four product areas",async()=>{
    const fetchMock=vi.spyOn(globalThis,"fetch")
      .mockResolvedValueOnce(new Response(null,{status:401}))
      .mockResolvedValueOnce(json({username:"owner"}))
      .mockResolvedValueOnce(json([]))
      .mockResolvedValueOnce(json(emptyToday))
      .mockResolvedValueOnce(json({items:[],has_more:false}))
      .mockResolvedValueOnce(json(prefs))
      .mockResolvedValueOnce(json([]))
      .mockResolvedValueOnce(json({items:[{id:"e1",kind:"episode",content:"Launch mapped",actor:"joint",created_at:"2026-10-01T08:00:00Z",version:1,editable:true,provenance_target_id:"e1"}],has_more:false}));
    render(<Page/>);
    fireEvent.change(await screen.findByLabelText("Access code"),{target:{value:"secret"}});
    fireEvent.click(screen.getByRole("button",{name:"Sign in"}));
    const nav=await screen.findByRole("navigation",{name:"Primary"});
    const buttons=within(nav).getAllByRole("button");
    expect(buttons).toHaveLength(4);
    for(const label of ["Chat","Today","Threads","History"]) expect(within(nav).getByRole("button",{name:label})).toBeInTheDocument();
    fireEvent.click(within(nav).getByRole("button",{name:"History"}));
    expect(await screen.findByText("Launch mapped")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(call=>String(call[0]).includes("/api/history/timeline"))).toBe(true);
  });

  it("shows a retryable load error and session-expiry message",async()=>{
    vi.spyOn(globalThis,"fetch")
      .mockResolvedValueOnce(json([]))
      .mockResolvedValueOnce(new Response(null,{status:503}))
      .mockResolvedValueOnce(json(emptyToday))
      .mockResolvedValueOnce(json({items:[],has_more:false}));
    render(<Page/>);
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not load/i);
    expect(screen.getByRole("button",{name:"Try again"})).toBeInTheDocument();
  });
});

describe("Threads correction",()=>{
  const item:ThreadItem={id:"t1",title:"Model lab",description:"Explore",state:"active",importance:2,deadline:null,next_action:"Test",watch:false,version:1,created_at:"2026-10-01T08:00:00Z",derivation:"explicit"};
  it("filters groups, validates edits, and reports stale conflicts",async()=>{
    vi.spyOn(globalThis,"fetch").mockResolvedValue(json({detail:"Version conflict"},409));
    render(<Threads items={[item]} onSessionExpired={()=>undefined}/>);
    fireEvent.click(screen.getByRole("button",{name:"Edit Model lab"}));
    fireEvent.change(screen.getByLabelText("Title"),{target:{value:"   "}});
    fireEvent.click(screen.getByRole("button",{name:"Save changes"}));
    expect(screen.getByRole("alert")).toHaveTextContent("Title is required");
    fireEvent.change(screen.getByLabelText("Title"),{target:{value:"Model lab revised"}});
    fireEvent.click(screen.getByRole("button",{name:"Save changes"}));
    expect(await screen.findByText(/changed somewhere else/i)).toBeInTheDocument();
  });
});

describe("History correction",()=>{
  const item:TimelineItem={id:"e1",kind:"episode",content:"Shared launch",actor:"joint",created_at:"2026-10-01T08:00:00Z",version:1,editable:true,provenance_target_id:"e1"};
  it("edits a retained episode with CAS",async()=>{
    const onReload=vi.fn();
    vi.spyOn(globalThis,"fetch")
      .mockResolvedValueOnce(json({...item,content:"Corrected launch",summary:"Shared launch",version:1}))
      .mockResolvedValueOnce(json({...item,content:"Corrected launch",summary:"Corrected launch",version:2}));
    render(<History items={[item]} onReload={onReload} onSessionExpired={()=>undefined}/>);
    fireEvent.click(screen.getByRole("button",{name:"Edit Shared launch"}));
    fireEvent.change(screen.getByLabelText("Memory text"),{target:{value:" Corrected launch "}});
    fireEvent.click(screen.getByRole("button",{name:"Save correction"}));
    await waitFor(()=>expect(onReload).toHaveBeenCalled());
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/episodes/e1"),expect.objectContaining({method:"PATCH"}));
  });

  it("searches and requires confirmation before delete",async()=>{
    const onReload=vi.fn();
    vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(null,{status:204}));
    render(<History items={[item]} onReload={onReload} onSessionExpired={()=>undefined}/>);
    expect(screen.getByText("Joint")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"Delete Shared launch"}));
    expect(screen.getByRole("dialog",{name:"Delete memory?"})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"Delete permanently"}));
    await waitFor(()=>expect(onReload).toHaveBeenCalled());
  });
});
