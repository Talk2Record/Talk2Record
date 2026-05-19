"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { formatCurrency, formatDate } from "@/lib/format";
import { recordsService } from "@/services/platform-service";
import { Input } from "@/shared/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import RecordsLoading from "@/app/dashboard/records/loading";

export default function RecordsPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["records"],
    queryFn: recordsService.list,
  });
  const [customerFilter, setCustomerFilter] = useState("");
  const [productFilter, setProductFilter] = useState("");

  const filtered = useMemo(
    () =>
      data.filter(
        (item) =>
          item.customer.toLowerCase().includes(customerFilter.toLowerCase()) &&
          item.product.toLowerCase().includes(productFilter.toLowerCase())
      ),
    [customerFilter, data, productFilter]
  );

  if (isLoading) {
    return <RecordsLoading />;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Record review
        </div>
        <h1>Records</h1>
        <p className="text-muted-foreground">
          Filter extracted records by customer or product before export or downstream automation.
        </p>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Date, product, amount, and customer filters can map to backend params later.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <Input
            placeholder="Filter by customer"
            value={customerFilter}
            onChange={(event) => setCustomerFilter(event.target.value)}
          />
          <Input
            placeholder="Filter by product"
            value={productFilter}
            onChange={(event) => setProductFilter(event.target.value)}
          />
        </CardContent>
      </Card>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Extracted records</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="text-muted-foreground">
              <tr className="border-primary/10 border-b">
                <th className="py-3 pr-4">Date</th>
                <th className="py-3 pr-4">Customer</th>
                <th className="py-3 pr-4">Product</th>
                <th className="py-3 pr-4">Quantity</th>
                <th className="py-3 pr-4">Amount</th>
                <th className="py-3 pr-4">Payment Method</th>
                <th className="py-3 pr-4">Voice Transcript</th>
                <th className="py-3">Confidence Score</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id} className="border-primary/10 border-b align-top">
                  <td className="py-4 pr-4">{formatDate(item.date)}</td>
                  <td className="py-4 pr-4 font-medium">{item.customer}</td>
                  <td className="py-4 pr-4">{item.product}</td>
                  <td className="py-4 pr-4">{item.quantity}</td>
                  <td className="py-4 pr-4">{formatCurrency(item.amount, item.currency)}</td>
                  <td className="py-4 pr-4">{item.paymentMethod}</td>
                  <td className="text-muted-foreground py-4 pr-4">{item.transcript}</td>
                  <td className="py-4">{Math.round(item.confidenceScore * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
