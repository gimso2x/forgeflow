import { useState, useEffect, useCallback, useMemo } from "react";
import DataTable from "./DataTable";
import { fetchItems, addItem, updateItem, deleteItem } from "./api";
import type { Item } from "./api";

export default function Dashboard() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const data = await fetchItems();
    setItems(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async (name: string, status: string) => {
    await addItem({ name, status });
    await load();
  };

  const handleUpdate = async (id: number, name: string, status: string) => {
    await updateItem(id, { name, status });
    await load();
  };

  const handleDelete = async (id: number) => {
    await deleteItem(id);
    await load();
  };

  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    return items.filter(item =>
      item.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [items, searchQuery]);

  return (
    <div style={{ padding: 24 }}>
      <h1>Dashboard</h1>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <DataTable
          items={filteredItems}
          onAdd={handleAdd}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
          searchQuery={searchQuery}
          onSearch={setSearchQuery}
        />
      )}
    </div>
  );
}
