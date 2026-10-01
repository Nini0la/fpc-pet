import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {afterEach,describe,expect,it,vi} from "vitest";
import Chat from "../app/chat";
import Page from "../app/page";

afterEach(()=>vi.restoreAllMocks());

describe("Chat",()=>{
  it("renders untrusted message as text without creating executable markup",()=>{
    const payload='<img src=x onerror=alert(1)>';
    render(<Chat initialMessages={[{id:"1",role:"user",content:payload}]}/>);
    expect(screen.getByText(payload)).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });

  it("shows the bounded message capacity",()=>{
    render(<Chat/>);
    expect(screen.getByText("0 / 4000")).toBeInTheDocument();
  });
});

describe("Page",()=>{
  it("fetches and renders prior messages immediately after login",async()=>{
    const prior=[
      {id:"1",role:"user",content:"Earlier question"},
      {id:"2",role:"assistant",content:"Earlier answer"},
    ];
    const fetchMock=vi.spyOn(globalThis,"fetch")
      .mockResolvedValueOnce(new Response(null,{status:401}))
      .mockResolvedValueOnce(new Response(null,{status:200}))
      .mockResolvedValueOnce(new Response(JSON.stringify(prior),{
        status:200,
        headers:{"content-type":"application/json"},
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        local_date:"2026-09-30",briefing:null,vocabulary:null,power_list:[],open_commitments:[],
        resurfaced_items:[],evening_reflection:{status:"not_started",journal:null},
      }),{status:200,headers:{"content-type":"application/json"}}))
      .mockResolvedValueOnce(new Response(JSON.stringify({items:[],has_more:false}),{
        status:200,headers:{"content-type":"application/json"},
      }));

    render(<Page/>);
    await screen.findByLabelText("Access code");
    fireEvent.change(screen.getByLabelText("Access code"),{target:{value:"secret"}});
    fireEvent.click(screen.getByRole("button",{name:"Sign in"}));

    expect(await screen.findByText("Earlier question")).toBeInTheDocument();
    expect(screen.getByText("Earlier answer")).toBeInTheDocument();
    await waitFor(()=>expect(fetchMock).toHaveBeenCalledTimes(5));
    expect(fetchMock.mock.calls[2][0]).toBe("http://localhost:8000/api/chat/messages");
    expect(fetchMock.mock.calls[3][0]).toBe("http://localhost:8000/api/today");
    expect(fetchMock.mock.calls[4][0]).toBe("http://localhost:8000/api/vocabulary?limit=20&offset=0");
  });

  it("renders Today data for an authenticated user",async()=>{
    const today={
      local_date:"2026-09-30",
      briefing:{content:"Morning continuity",local_date:"2026-09-30"},
      vocabulary:null,
      power_list:[],
      open_commitments:[],
      resurfaced_items:[],
      evening_reflection:{status:"not_started",journal:null},
    };
    vi.spyOn(globalThis,"fetch")
      .mockResolvedValueOnce(new Response("[]",{status:200,headers:{"content-type":"application/json"}}))
      .mockResolvedValueOnce(new Response(JSON.stringify(today),{status:200,headers:{"content-type":"application/json"}}))
      .mockResolvedValueOnce(new Response(JSON.stringify({items:[],has_more:false}),{status:200,headers:{"content-type":"application/json"}}));

    render(<Page/>);

    expect(await screen.findByRole("heading",{name:"Today"})).toBeInTheDocument();
    expect(screen.getByText("Morning continuity")).toBeInTheDocument();
  });
});
