package generator_uml.back_generator_uml.configuration;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.cors.CorsConfiguration;

import static org.assertj.core.api.Assertions.assertThat;

class SecurityConfigurationTest {

    private static final String TUNEL_ACTUAL = "https://spectrum-opinion-yeast-permanent.trycloudflare.com";

    @Test
    void parseOrigins_ignoraNulosVaciosYEspacios() {
        assertThat(SecurityConfiguration.parseOrigins(null)).isEmpty();
        assertThat(SecurityConfiguration.parseOrigins("")).isEmpty();
        assertThat(SecurityConfiguration.parseOrigins(" , ,")).isEmpty();
        assertThat(SecurityConfiguration.parseOrigins(" https://a.example.com , https://b.example.com ,"))
                .containsExactly("https://a.example.com", "https://b.example.com");
    }

    @Test
    void sinVariable_conservaLosOrigenesPorDefecto() {
        CorsConfiguration cors = corsFor(new SecurityConfiguration(""));

        assertThat(cors.getAllowedOrigins())
                .contains(TUNEL_ACTUAL, "http://18.188.167.127:4200", "http://localhost:4200");
        assertThat(cors.checkOrigin("https://desconocido.example.com")).isNull();
    }

    @Test
    void conVariable_sumaLosNuevosSinQuitarLosExistentes() {
        CorsConfiguration cors = corsFor(new SecurityConfiguration(
                "https://nuevo.trycloudflare.com, https://otro.example.com"));

        assertThat(cors.checkOrigin("https://nuevo.trycloudflare.com")).isEqualTo("https://nuevo.trycloudflare.com");
        assertThat(cors.checkOrigin("https://otro.example.com")).isEqualTo("https://otro.example.com");
        assertThat(cors.checkOrigin(TUNEL_ACTUAL)).isEqualTo(TUNEL_ACTUAL);
    }

    @Test
    void noDuplicaOrigenesRepetidos() {
        CorsConfiguration cors = corsFor(new SecurityConfiguration(TUNEL_ACTUAL));

        assertThat(cors.getAllowedOrigins()).filteredOn(TUNEL_ACTUAL::equals).hasSize(1);
    }

    private static CorsConfiguration corsFor(SecurityConfiguration configuration) {
        return configuration.corsConfigurationSource()
                .getCorsConfiguration(new MockHttpServletRequest("OPTIONS", "/generate"));
    }
}
