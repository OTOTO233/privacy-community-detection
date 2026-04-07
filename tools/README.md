# tools

本目录用于存放 `mLFR Benchmark` 相关的第三方工具和桥接文件。

当前仓库提交的是目录骨架，便于：

- 保留项目约定的工具路径；
- 让 `tools/` 目录本身进入 Git 管理；
- 后续补充或替换外部二进制、源码包和桥接文件。

当前约定的子目录：

- `mLFR_app_v04/`：官方应用包位置
- `mLFR_code_v04/`：官方源码包位置
- `mLFR-benchmark-master/`：官方仓库镜像位置
- `mlfr_lib/`：Java 依赖 jar 位置
- `mlfr_bridge/`：本项目 Java 桥接文件位置

如果需要重新恢复完整工具链，可将对应文件放回这些目录。
