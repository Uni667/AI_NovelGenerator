"use client"
 
import React, { useState } from "react"
import { WorkbenchSidebar } from "./workbench/WorkbenchSidebar"
import { WorkbenchEditor } from "./workbench/WorkbenchEditor"
import { WorkbenchStatusPane } from "./workbench/WorkbenchStatusPane"
import { Button } from "@/components/ui/button"
import { PanelRightClose, PanelRightOpen, Maximize2, Minimize2, PanelLeftClose, PanelLeftOpen } from "lucide-react"
 
export function WorkbenchTab() {
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightPanelOpen, setRightPanelOpen] = useState(true)
  const [focusMode, setFocusMode] = useState(false)
 
  const sidebarWidth = leftSidebarOpen && !focusMode ? "260px" : "0px"
  const statusWidth = rightPanelOpen && !focusMode ? "300px" : "0px"
 
  return (
    <div
      className="flex-1 min-h-0 flex flex-col gap-4 xl:grid xl:gap-4 xl:transition-all xl:duration-300"
      style={{
        gridTemplateColumns: focusMode
          ? "0px minmax(0,1fr) 0px"
          : `${sidebarWidth} minmax(0,1fr) ${statusWidth}`,
      }}
    >
      {/* 侧边栏章节列表 */}
      <div
        className={`xl:min-h-0 shrink-0 max-h-[35vh] xl:max-h-full overflow-hidden transition-all duration-300 ${
          !leftSidebarOpen || focusMode 
            ? "xl:opacity-0 xl:pointer-events-none xl:w-0 xl:overflow-hidden" 
            : "xl:w-[260px]"
        }`}
      >
        <WorkbenchSidebar />
      </div>
 
      {/* 编辑器 —— 主工作区（含浮动控制按钮） */}
      <div className="xl:min-h-0 flex-1 min-h-[35vh] xl:min-h-0 min-w-0 flex flex-col">
        {/* 浮动控制条 */}
        <div className="hidden xl:flex items-center justify-end gap-1 mb-2 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
            className="h-7 px-2 text-muted-foreground hover:text-foreground"
            title={leftSidebarOpen ? "折叠左侧目录" : "展开左侧目录"}
          >
            {leftSidebarOpen ? <PanelLeftClose className="h-3.5 w-3.5" /> : <PanelLeftOpen className="h-3.5 w-3.5" />}
            <span className="ml-1 text-[11px]">{leftSidebarOpen ? "折叠目录" : "展开目录"}</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setFocusMode(!focusMode)}
            className="h-7 px-2 text-muted-foreground hover:text-foreground"
            title={focusMode ? "退出专注模式" : "专注写作模式"}
          >
            {focusMode ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
            <span className="ml-1 text-[11px]">{focusMode ? "退出专注" : "专注模式"}</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            className="h-7 px-2 text-muted-foreground hover:text-foreground"
            title={rightPanelOpen ? "折叠右侧面板" : "展开右侧面板"}
          >
            {rightPanelOpen ? <PanelRightClose className="h-3.5 w-3.5" /> : <PanelRightOpen className="h-3.5 w-3.5" />}
            <span className="ml-1 text-[11px]">{rightPanelOpen ? "折叠属性" : "展开属性"}</span>
          </Button>
        </div>
        <WorkbenchEditor />
      </div>
 
      {/* 状态与质检面板 */}
      <div
        className={`xl:min-h-0 shrink-0 max-h-[30vh] xl:max-h-full overflow-hidden transition-all duration-300 ${
          !rightPanelOpen || focusMode 
            ? "xl:opacity-0 xl:pointer-events-none xl:w-0 xl:overflow-hidden" 
            : "xl:w-[300px]"
        }`}
      >
        <WorkbenchStatusPane />
      </div>
    </div>
  )
}
