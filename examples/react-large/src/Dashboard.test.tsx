import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import Dashboard from "./Dashboard";
import { _resetItems } from "./api";

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  _resetItems();
});

describe("Dashboard", () => {
  it("renders dashboard header", async () => {
    render(<Dashboard />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });
  });

  it("renders table with initial items", async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
      expect(screen.getByText("Beta")).toBeInTheDocument();
    });
  });

  it("can add an item", async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("new-item-name"), {
      target: { value: "Gamma" },
    });
    fireEvent.change(screen.getByLabelText("new-item-status"), {
      target: { value: "active" },
    });
    fireEvent.click(screen.getByText("Add"));

    await waitFor(() => {
      expect(screen.getByText("Gamma")).toBeInTheDocument();
    });
  });

  it("can delete an item", async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
    });
  });

  it("can search items by name", async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
      expect(screen.getByText("Beta")).toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText("search-items");
    fireEvent.change(searchInput, { target: { value: "Alpha" } });

    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
  });
});
