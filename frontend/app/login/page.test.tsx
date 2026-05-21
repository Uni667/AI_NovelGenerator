import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LoginPage from "./page";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

// Mock auth module
vi.mock("@/lib/auth", () => ({
  login: vi.fn(),
  register: vi.fn(),
  setToken: vi.fn(),
  setUser: vi.fn(),
}));

// Mock UI components
vi.mock("@/components/ui/card", () => ({
  Card: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardContent: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardDescription: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardHeader: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardTitle: ({ children, className }: any) => <div className={className}>{children}</div>,
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({ children, className, onClick, disabled, type }: any) => (
    <button className={className} onClick={onClick} disabled={disabled} type={type}>
      {children}
    </button>
  ),
}));

vi.mock("@/components/ui/input", () => ({
  Input: ({ value, onChange, placeholder, type, autoFocus, ...props }: any) => (
    <input value={value} onChange={onChange} placeholder={placeholder} type={type} autoFocus={autoFocus} {...props} />
  ),
}));

vi.mock("@/components/ui/label", () => ({
  Label: ({ children }: any) => <label>{children}</label>,
}));

vi.mock("lucide-react", () => ({
  BookOpen: () => <svg data-testid="book-icon" />,
}));

import { login } from "@/lib/auth";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form by default", () => {
    render(<LoginPage />);
    expect(screen.getByText("AI 小说生成器")).toBeTruthy();
    expect(screen.getByText("登录你的账户")).toBeTruthy();
    expect(screen.getByLabelText("用户名")).toBeTruthy();
    expect(screen.getByLabelText("密码")).toBeTruthy();
  });

  it("shows error when submitting empty form", async () => {
    render(<LoginPage />);
    const submitButton = screen.getByRole("button", { name: "登录" });
    fireEvent.click(submitButton);
    expect(await screen.findByText("请填写用户名和密码")).toBeTruthy();
  });

  it("switches to register mode", () => {
    render(<LoginPage />);
    const toggleButton = screen.getByText("去注册");
    fireEvent.click(toggleButton);
    expect(screen.getByText("创建新账户")).toBeTruthy();
    expect(screen.getByLabelText("确认密码")).toBeTruthy();
  });

  it("shows error when passwords do not match in register mode", async () => {
    render(<LoginPage />);
    fireEvent.click(screen.getByText("去注册"));

    fireEvent.change(screen.getByLabelText("用户名"), { target: { value: "testuser" } });
    fireEvent.change(screen.getAllByLabelText("密码")[0], { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText("确认密码"), { target: { value: "different" } });

    fireEvent.click(screen.getByRole("button", { name: "注册" }));
    expect(await screen.findByText("两次密码不一致")).toBeTruthy();
  });

  it("shows error when password is too short in register mode", async () => {
    render(<LoginPage />);
    fireEvent.click(screen.getByText("去注册"));

    fireEvent.change(screen.getByLabelText("用户名"), { target: { value: "testuser" } });
    fireEvent.change(screen.getAllByLabelText("密码")[0], { target: { value: "123" } });
    fireEvent.change(screen.getByLabelText("确认密码"), { target: { value: "123" } });

    fireEvent.click(screen.getByRole("button", { name: "注册" }));
    expect(await screen.findByText("密码至少 6 位")).toBeTruthy();
  });

  it("calls login API on successful login", async () => {
    const mockLogin = vi.mocked(login);
    mockLogin.mockResolvedValue({ token: "fake-token", user_id: "123", username: "testuser" });

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("用户名"), { target: { value: "testuser" } });
    fireEvent.change(screen.getByLabelText("密码"), { target: { value: "password123" } });

    fireEvent.click(screen.getByRole("button", { name: "登录" }));

    expect(mockLogin).toHaveBeenCalledWith("testuser", "password123");
  });

  it("shows loading state during submission", () => {
    const mockLogin = vi.mocked(login);
    mockLogin.mockImplementation(() => new Promise(() => {}));

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("用户名"), { target: { value: "testuser" } });
    fireEvent.change(screen.getByLabelText("密码"), { target: { value: "password123" } });

    fireEvent.click(screen.getByRole("button", { name: "登录" }));
    expect(screen.getByText("处理中...")).toBeTruthy();
  });
});
