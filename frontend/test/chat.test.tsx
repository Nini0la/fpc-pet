import {render,screen} from "@testing-library/react"; import {describe,expect,it} from "vitest"; import Chat from "../app/chat";
describe("Chat",()=>{
  it("renders untrusted message as text without creating executable markup",()=>{const payload='<img src=x onerror=alert(1)>'; render(<Chat initialMessages={[{id:"1",role:"user",content:payload}]}/>); expect(screen.getByText(payload)).toBeInTheDocument(); expect(document.querySelector("img")).toBeNull();});
  it("shows the bounded message capacity",()=>{render(<Chat/>);expect(screen.getByText("0 / 4000")).toBeInTheDocument();});
});
