#!groovy

/// file: test-unixcat.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Compile & Test Unixcat') {
                sh("GCC_TOOLCHAIN=/opt/gcc-13.2.0 packages/unixcat/run --clean --all");
            }
        }
        stage("Analyse Issues") {
            publishIssues(
                issues: [scanForIssues( tool: gcc())],
                trendChartType: 'TOOLS_ONLY',
                qualityGates: [[
                    threshold: 1,
                    type: 'TOTAL',
                    unstable: false,
                ]],
            );
        }
    }
}

return this;
