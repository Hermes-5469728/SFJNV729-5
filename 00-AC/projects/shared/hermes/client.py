class HermesClient:
    def read_data(self, endpoint: str) -> None:
        print(f"[HermesClient] 正在从 {endpoint} 读取数据...")
        print(f"[HermesClient] 数据传输完成。")

    def write_data(self, endpoint: str, payload) -> None:
        print(f"[HermesClient] 正在向 {endpoint} 写入数据...")
        print(f"[HermesClient] 负载: {payload}")
        print(f"[HermesClient] 数据传输完成。")
