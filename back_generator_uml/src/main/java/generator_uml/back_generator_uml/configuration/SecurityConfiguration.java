package generator_uml.back_generator_uml.configuration;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

@Configuration
@EnableWebSecurity
public class SecurityConfiguration {

    private static final List<String> DEFAULT_ALLOWED_ORIGINS = List.of(
            "http://localhost:3000",
            "http://localhost:4200",
            "http://localhost:4000",
            "http://ec2-3-84-241-46.compute-1.amazonaws.com:4000",
            "https://front-sw1.fournext.me",
            "http://18.188.167.127:4200",
            "https://spectrum-opinion-yeast-permanent.trycloudflare.com"
    );

    private final List<String> extraAllowedOrigins;

    // Origenes adicionales sin recompilar: variable de entorno APP_CORS_ALLOWED_ORIGINS
    // (o la propiedad app.cors.allowed-origins), separados por coma. Se SUMAN a los de arriba.
    // Util cuando el Quick Tunnel de Cloudflare cambia de direccion al reiniciarse.
    public SecurityConfiguration(@Value("${app.cors.allowed-origins:}") String extraAllowedOrigins) {
        this.extraAllowedOrigins = parseOrigins(extraAllowedOrigins);
    }

    static List<String> parseOrigins(String csv) {
        if (csv == null) {
            return List.of();
        }
        return Arrays.stream(csv.split(","))
                .map(String::trim)
                .filter(origin -> !origin.isEmpty())
                .toList();
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .cors(cors -> cors.configurationSource(corsConfigurationSource()));

        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        Set<String> origins = new LinkedHashSet<>(DEFAULT_ALLOWED_ORIGINS);
        origins.addAll(extraAllowedOrigins);

        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(new ArrayList<>(origins));
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("Authorization", "Content-Type"));
        configuration.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
}
