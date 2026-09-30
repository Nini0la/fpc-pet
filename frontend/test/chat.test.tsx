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
      }));

    render(<Page/>);
    await screen.findByLabelText("Access code");
    fireEvent.change(screen.getByLabelText("Access code"),{target:{value:"secret"}});
    fireEvent.click(screen.getByRole("button",{name:"Sign in"}));

    expect(await screen.findByText("Earlier question")).toBeInTheDocument();
    expect(screen.getByText("Earlier answer")).toBeInTheDocument();
    await waitFor(()=>expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(fetchMock.mock.calls[2][0]).toBe("http://localhost:8000/api/chat/messages");
  });
});
