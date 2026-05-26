"use client"

import React from "react"
import { WorkbenchSidebar } from "./workbench/WorkbenchSidebar"
import { WorkbenchEditor } from "./workbench/WorkbenchEditor"
import { WorkbenchStatusPane } from "./workbench/WorkbenchStatusPane"

export function WorkbenchTab() {
  return (
    <div className="flex-1 min-h-0 grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)_320px] h-auto xl:h-[55vh]">
      <div className="h-[300px] xl:h-full">
        <WorkbenchSidebar />
      </div>
      <div className="h-[450px] xl:h-full">
        <WorkbenchEditor />
      </div>
      <div className="h-auto xl:h-full">
        <WorkbenchStatusPane />
      </div>
    </div>
  )
}
