import {render,screen} from "@testing-library/react";
import {describe,expect,it} from "vitest";
import Today,{type TodayData} from "../app/today";

const data:TodayData={
  local_date:"2026-09-30",
  briefing:{content:"Good morning.",local_date:"2026-09-30"},
  power_list:[{id:"1",title:"Submit demo",reason:"deadline: Friday",kind:"commitment",score:40}],
  open_commitments:[{id:"1",title:"Submit demo",deadline_hint:"Friday"}],
  resurfaced_items:[{id:"2",title:"Write docs"}],
  evening_reflection:{status:"awaiting",journal:null},
};

describe("Today",()=>{
  it("renders the briefing, ranked reasons, resurfacing, and reflection state",()=>{
    render(<Today data={data}/>);
    expect(screen.getByRole("heading",{name:"Today"})).toBeInTheDocument();
    expect(screen.getByText("Good morning.")).toBeInTheDocument();
    expect(screen.getByText("Submit demo")).toBeInTheDocument();
    expect(screen.getByText("deadline: Friday")).toBeInTheDocument();
    expect(screen.getByText("Write docs")).toBeInTheDocument();
    expect(screen.getByText("Evening reflection: awaiting")).toBeInTheDocument();
  });

  it("does not fabricate absent sections",()=>{
    render(<Today data={{...data,briefing:null,power_list:[],open_commitments:[],resurfaced_items:[]}}/>);
    expect(screen.queryByText("Power List")).toBeNull();
    expect(screen.queryByText("Resurfaced")).toBeNull();
  });
});
