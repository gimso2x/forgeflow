import { useState } from "react";
import type { Item } from "./api";

interface DataTableProps {
  items: Item[];
  onAdd: (name: string, status: string) => void;
  onUpdate: (id: number, name: string, status: string) => void;
  onDelete: (id: number) => void;
  searchQuery?: string;
  onSearch?: (query: string) => void;
}

export default function DataTable({ items, onAdd, onUpdate, onDelete, searchQuery = "", onSearch }: DataTableProps) {
  const [newName, setNewName] = useState("");
  const [newStatus, setNewStatus] = useState("");
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editStatus, setEditStatus] = useState("");

  const handleAdd = () => {
    if (!newName.trim()) return;
    onAdd(newName, newStatus);
    setNewName("");
    setNewStatus("");
  };

  const startEdit = (item: Item) => {
    setEditId(item.id);
    setEditName(item.name);
    setEditStatus(item.status);
  };

  const handleSave = () => {
    if (editId === null) return;
    onUpdate(editId, editName, editStatus);
    setEditId(null);
    setEditName("");
    setEditStatus("");
  };

  return (
    <div>
      {onSearch && (
        <div style={{ marginBottom: 12 }}>
          <input
            placeholder="Search by name..."
            value={searchQuery}
            onChange={(e) => onSearch(e.target.value)}
            aria-label="search-items"
          />
        </div>
      )}
      <div style={{ marginBottom: 16 }}>
        <input
          placeholder="Name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          aria-label="new-item-name"
        />
        <input
          placeholder="Status"
          value={newStatus}
          onChange={(e) => setNewStatus(e.target.value)}
          aria-label="new-item-status"
        />
        <button onClick={handleAdd}>Add</button>
      </div>

      <table border={1} cellPadding={8}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>
                {editId === item.id ? (
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    aria-label="edit-name"
                  />
                ) : (
                  item.name
                )}
              </td>
              <td>
                {editId === item.id ? (
                  <input
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value)}
                    aria-label="edit-status"
                  />
                ) : (
                  item.status
                )}
              </td>
              <td>
                {editId === item.id ? (
                  <button onClick={handleSave}>Save</button>
                ) : (
                  <>
                    <button onClick={() => startEdit(item)}>Edit</button>
                    <button onClick={() => onDelete(item.id)}>Delete</button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={4}>No items</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
