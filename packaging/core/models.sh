# The two models the core places backgrounds with (ADR-0120): the one place
# they are pinned. OpenCV's model zoo at a fixed commit, each file checked.
#   YuNet (faces)            - MIT,        232 KB
#   YOLOX-S (people, animals) - Apache-2.0, 36 MB
MODELS_COMMIT="47534e27c9851bb1128ccc0102f1145e27f23f98"
MODELS_BASE="https://github.com/opencv/opencv_zoo/raw/${MODELS_COMMIT}/models"
FACE_MODEL_URL="${MODELS_BASE}/face_detection_yunet/face_detection_yunet_2023mar.onnx"
FACE_MODEL_SHA256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
SUBJECT_MODEL_URL="${MODELS_BASE}/object_detection_yolox/object_detection_yolox_2022nov.onnx"
SUBJECT_MODEL_SHA256="c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063"
