假设你拿到一个 `OrderController.java`，里面长这样：

```java
package com.superdupermart.shopping.controller.buyer;

import ...;  // 15 行 import

@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {
    private final OrderService orderService;
    private final ProductService productService;

    @PostMapping
    public ResponseEntity<OrderDto> placeOrder(@RequestBody PlaceOrderRequest req) {
        // 30 行业务逻辑
    }

    @GetMapping("/user")
    public List<OrderDto> getUserOrders() {
        // 10 行
    }

    @PatchMapping("/cancel")
    public ResponseEntity<Void> cancelOrder(@RequestParam Long orderId) {
        // 15 行
    }
}
```

**问题 1**：按方法切，这个文件会切出 3 个 chunk 还是 4 个？如果是 4 个，第 4 个是什么？

**问题 2**：`import` 语句和 `@RestController` / `@RequestMapping("/api/orders")` 这些**类级别**的信息，要不要塞进每个方法 chunk 里？如果塞，怎么塞；如果不塞，会出什么问题？

**问题 3**：如果用户问"`/api/orders/cancel` 这个 endpoint 在哪"，你期待系统检索出 `cancelOrder` 方法的 chunk。但 `@PatchMapping("/cancel")` 里只有 `"/cancel"`——完整路径 `/api/orders/cancel` 是**类级别的 `@RequestMapping` 和方法级别的 `@PatchMapping` 拼起来的**。你的 chunk 里要不要保存这个拼好的完整路径？存在哪里？

**问题 4**：`OrderService orderService` 这个字段（被 `@RequiredArgsConstructor` 注入），它算 `placeOrder` 方法这个 chunk 的一部分，还是独立出来？

## 问题 1：

**我的建议：第 4 个 chunk 是 "class header chunk"**，内容是：

- package 声明
- imports
- 类级 Javadoc
- 类级注解（`@RestController`、`@RequestMapping`）
- 类声明行（`public class OrderController {`）
- 字段声明（`private final OrderService orderService;`）

**为什么需要这个独立 chunk**？考虑这个 query：

> "OrderController 依赖哪些 service？"

这个问题的答案**不在任何一个方法里**，而在字段声明那一段。如果你把字段并进每个方法 chunk（你问题 4 的答案），那系统检索时会召回 3 个方法 chunk 都带着同样的字段声明——**冗余、重复、浪费 top-k 名额**。独立出来只需要一个 chunk 就解决了。

这也回答了你问题 4：字段不属于某个特定方法，它属于"类头"这个独立 chunk。

## 问题 2：方向对，但"全塞进去"会出问题

我的建议：

- **塞进方法 chunk**：类名、类级 `@RequestMapping` 的 URL 前缀、方法所属的 role scope（buyer/seller）
- **不塞进方法 chunk**：完整 import 列表、类 Javadoc、字段声明、无关的类级注解

**实现上，不是拼接原文，而是加 metadata + 一行"类头摘要"。** 形式长这样：

```java
// ===== Context =====
// Class: OrderController
// Package: com.superdupermart.shopping.controller.buyer
// Class-level mapping: @RequestMapping("/api/orders")
// Role: buyer
// ===== Method =====
@PostMapping
public ResponseEntity<OrderDto> placeOrder(@RequestBody PlaceOrderRequest req) {
    ...
}
```

这样既保留了 LLM 理解方法所需的上下文，又不会让三个方法 chunk 的向量趋同。

## 问题 3：

**我的建议：要拼，而且要存 metadata，不是只存正文。**

```python
chunk.metadata = {
    "chunk_id": "ordercontroller_cancelOrder_L58",
    "class_name": "OrderController",
    "method_name": "cancelOrder",
    "http_method": "PATCH",
    "endpoint_path": "/api/orders/cancel",   # 拼好的完整路径
    "layer": "controller",
    "role_scope": "buyer",
    ...
}
```

**为什么要单独存 metadata 而不是只写在正文里**？三个原因：

1. **BM25 能直接命中**：V2 做 hybrid retrieval 时，用户问 "`/api/orders/cancel` 在哪"，你可以做一个 metadata-level 的精确匹配 + BM25 + dense，三路融合。metadata 匹配是最准的。
2. **V3 graph extraction 免费**：V3 你要抽 `Endpoint` 节点，每个节点的 `path` 属性直接从 metadata 读，不用再 parse 一遍 annotation。
3. **eval dataset 的 `expected_source` 字段能精确引用**：你可以写 `expected_source: "OrderController.cancelOrder"` 或 `expected_endpoint: "/api/orders/cancel"`，两种都能精确匹配。

**你没答到的地方**：光把 annotation 文本塞进正文不够，LLM 看到 `@PatchMapping("/cancel")` 不一定能推断出完整路径是 `/api/orders/cancel`，它得同时看到类级的 `@RequestMapping`。如果你在 ingestion 阶段就**用 javalang 解析出来、拼好、写进 metadata**，检索精度直接上一个台阶。

## 问题 4：

理由上面讲了——字段声明属于"类头 chunk"，不属于任何一个方法。你答"算 placeOrder 的一部分"的直觉来源，大概是"placeOrder 里会用到 orderService，所以要放一起"。这个想法不对，原因：

- `cancelOrder` 也用 `orderService`，难道也给 cancelOrder chunk 复制一份？
- 字段定义在类的开头，距离任何方法都不远，chunking 不是物理切割，是**语义分组**。

类比一下：如果你把一本书切成章节 chunk，**书的目录** 应该单独是一个 chunk，还是复制到每一章开头？显然是前者。字段声明就是这本"类"之书的目录。

---

Chunking example:

注意字段的类型

```python
chunk_1:
  chunk_id: "OrderController_placeOrder_L42"
  fq_name: "com.superdupermart.shopping.controller.buyer.OrderController#placeOrder"
  source_path: "src/main/java/com/superdupermart/shopping/controller/buyer/OrderController.java"
  layer: "controller"
  role_scope: "buyer"
  package: "com.superdupermart.shopping.controller.buyer"
  class_name: "OrderController"
  method_name: "placeOrder"
  http_method: "POST"
  endpoint_path: "/api/orders"
  annotations: ["@PostMapping"]
  start_line: 42
  end_line: 72

chunk_2:
  chunk_id: "OrderController_getUserOrders_L74"
  fq_name: "com.superdupermart.shopping.controller.buyer.OrderController#getUserOrders"
  source_path: ".../OrderController.java"
  layer: "controller"
  role_scope: "buyer"
  package: "com.superdupermart.shopping.controller.buyer"
  class_name: "OrderController"
  method_name: "getUserOrders"
  http_method: "GET"
  endpoint_path: "/api/orders/user"
  annotations: ["@GetMapping"]
  start_line: 74
  end_line: 85

chunk_3:
  chunk_id: "OrderController_cancelOrder_L87"
  fq_name: "com.superdupermart.shopping.controller.buyer.OrderController#cancelOrder"
  source_path: ".../OrderController.java"
  layer: "controller"
  role_scope: "buyer"
  package: "com.superdupermart.shopping.controller.buyer"
  class_name: "OrderController"
  method_name: "cancelOrder"
  http_method: "PATCH"
  endpoint_path: "/api/orders/cancel"
  annotations: ["@PatchMapping"]
  start_line: 87
  end_line: 102
  ```

还有一类字段:
```python
calls: 这个方法调用了哪些其他方法（["orderService.createOrder", "productService decrementStock"]）
returns: 返回类型（"ResponseEntity<OrderDto>"）
params: 参数列表（[{"name": "req", "type": "PlaceOrderRequest"}]）
throws: 可能抛的异常
```
